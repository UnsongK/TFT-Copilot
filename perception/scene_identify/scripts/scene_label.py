import os
import json
import glob
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk


class SceneAnnotator:
	def __init__(self, master):
		self.master = master
		self.master.title('Scene Annotator')

		# state
		self.image_dir = ''
		self.images = []
		self.idx = 0
		self.image = None
		self.photo = None
		self.scale = 1.0
		self.current_image_path = None

		# annotations for current image: list of dict {'label': str, 'points': [[x,y]...], 'rect_id': canvas_id}
		self.annotations = []

		# UI
		ctrl = tk.Frame(master)
		ctrl.pack(side=tk.TOP, fill=tk.X)

		tk.Label(ctrl, text='Scene name:').pack(side=tk.LEFT, padx=4)
		self.scene_var = tk.StringVar()
		self.scene_entry = tk.Entry(ctrl, textvariable=self.scene_var, width=30)
		self.scene_entry.pack(side=tk.LEFT, padx=4)

		btn_browse = tk.Button(ctrl, text='Open Folder', command=self.browse_folder)
		btn_browse.pack(side=tk.LEFT, padx=4)

		btn_prev = tk.Button(ctrl, text='Prev', command=self.prev_image)
		btn_prev.pack(side=tk.LEFT, padx=4)
		btn_next = tk.Button(ctrl, text='Next', command=self.next_image)
		btn_next.pack(side=tk.LEFT, padx=4)

		btn_undo = tk.Button(ctrl, text='Undo', command=self.undo)
		btn_undo.pack(side=tk.LEFT, padx=4)

		btn_save = tk.Button(ctrl, text='Save JSON', command=self.save_json)
		btn_save.pack(side=tk.LEFT, padx=4)

		info = tk.Label(ctrl, text='Draw rectangle with mouse; on release you will be asked for label.')
		info.pack(side=tk.LEFT, padx=8)

		# status and magnifier
		self.status_var = tk.StringVar(value='x,y: -')
		self.status_label = tk.Label(ctrl, textvariable=self.status_var)
		self.status_label.pack(side=tk.RIGHT, padx=8)

		self.magnifier_on = False
		btn_mag = tk.Button(ctrl, text='Toggle Magnifier', command=self.toggle_magnifier)
		btn_mag.pack(side=tk.RIGHT, padx=4)

		# canvas and list
		self.canvas = tk.Canvas(master, cursor='cross', bg='black')
		self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		self.canvas.bind('<ButtonPress-1>', self.on_button_press)
		self.canvas.bind('<B1-Motion>', self.on_move)
		self.canvas.bind('<ButtonRelease-1>', self.on_button_release)
		self.canvas.bind('<Motion>', self.on_mouse_move)

		# mouse wheel (Windows) and Linux support
		self.canvas.bind('<MouseWheel>', self.on_mouse_wheel)
		self.canvas.bind('<Button-4>', self.on_mouse_wheel)
		self.canvas.bind('<Button-5>', self.on_mouse_wheel)

		side = tk.Frame(master, width=240)
		side.pack(side=tk.RIGHT, fill=tk.Y)
		tk.Label(side, text='Annotations:').pack(anchor='nw')
		self.listbox = tk.Listbox(side, width=40)
		self.listbox.pack(fill=tk.Y, expand=True)

		# keyboard bindings
		master.bind('<Left>', lambda e: self.prev_image())
		master.bind('<Right>', lambda e: self.next_image())
		master.bind('z', lambda e: self.undo())
		master.bind('s', lambda e: self.save_json())

		# internal drawing
		self._start_x = None
		self._start_y = None
		self._rect_id = None
		# magnifier window and image ref
		self.mag_win = None
		self.mag_label = None
		self._mag_photo = None

	def browse_folder(self):
		folder = filedialog.askdirectory(initialdir='.')
		if not folder:
			return
		self.image_dir = folder
		self.load_images()
		self.idx = 0
		self.load_current_image()

	def load_images(self):
		exts = ('*.jpg', '*.jpeg', '*.png', '*.bmp')
		imgs = []
		for e in exts:
			imgs.extend(glob.glob(os.path.join(self.image_dir, e)))
		imgs = sorted(imgs)
		self.images = imgs

	def load_current_image(self):
		self.clear_canvas()
		if not self.images:
			messagebox.showinfo('Info', 'No images in folder')
			return
		path = self.images[self.idx]
		self.current_image_path = path
		img = Image.open(path).convert('RGB')
		iw, ih = img.size
		max_w, max_h = 1200, 800
		self.scale = min(1.0, max_w / iw, max_h / ih)
		disp = img.resize((int(iw * self.scale), int(ih * self.scale)), Image.LANCZOS)
		self.image = img
		self.photo = ImageTk.PhotoImage(disp)
		self.canvas.config(width=disp.width, height=disp.height)
		self.canvas.create_image(0, 0, anchor='nw', image=self.photo)
		# load annotations if json exists
		self.annotations = []
		json_path = os.path.splitext(path)[0] + '_scene.json'
		if os.path.exists(json_path):
			try:
				with open(json_path, 'r', encoding='utf-8') as f:
					j = json.load(f)
				self.scene_var.set(j.get('scene_name', ''))
				for ann in j.get('annotations', []):
					# points expected as list of four [x,y]
					pts = ann.get('points', [])
					# draw on canvas scaled
					rect_id = self._draw_rect_on_canvas(pts)
					self.annotations.append({'label': ann.get('label',''), 'points': pts, 'rect_id': rect_id})
				self.refresh_listbox()
			except Exception:
				pass
		else:
			self.refresh_listbox()

	def on_mouse_move(self, event):
		"""Update status coordinates and magnifier when mouse moves."""
		if self.photo is None or self.image is None:
			return
		# map canvas coords to original image coords
		x, y = event.x, event.y
		ix = int(round(x / self.scale))
		iy = int(round(y / self.scale))
		h, w = self.image.size[1], self.image.size[0]
		if 0 <= ix < w and 0 <= iy < h:
			self.status_var.set(f'x,y: {ix},{iy}')
		else:
			self.status_var.set('x,y: -')
		if self.magnifier_on:
			self.update_magnifier(ix, iy)


	def on_mouse_wheel(self, event):
		"""Zoom in/out on mouse wheel."""
		if self.image is None:
			return
		# determine direction
		if hasattr(event, 'delta'):
			if event.delta > 0:
				factor = 1.1
			else:
				factor = 0.9
		else:
			# Button-4 = up, Button-5 = down
			if event.num == 4:
				factor = 1.1
			else:
				factor = 0.9
		# clamp scale
		new_scale = self.scale * factor
		new_scale = max(0.1, min(new_scale, 5.0))
		self.scale = new_scale
		# redraw image and annotations
		self.redraw_all()


	def redraw_all(self):
		"""Redraw image and all annotation rectangles according to current scale."""
		if not self.current_image_path or self.image is None:
			return
		# redraw image
		iw, ih = self.image.size
		disp = self.image.resize((int(iw * self.scale), int(ih * self.scale)), Image.LANCZOS)
		self.photo = ImageTk.PhotoImage(disp)
		self.canvas.delete('all')
		self.canvas.config(width=disp.width, height=disp.height)
		self.canvas.create_image(0, 0, anchor='nw', image=self.photo)
		# redraw annotations
		for a in self.annotations:
			pts = a.get('points', [])
			rid = self._draw_rect_on_canvas(pts)
			a['rect_id'] = rid


	def toggle_magnifier(self):
		self.magnifier_on = not self.magnifier_on
		if not self.magnifier_on:
			# safely destroy magnifier window if it exists
			if self.mag_win:
				try:
					if callable(getattr(self.mag_win, 'winfo_exists', None)) and self.mag_win.winfo_exists():
						self.mag_win.destroy()
				except Exception:
					pass
			# clear references
			self.mag_win = None
			self.mag_label = None


	def update_magnifier(self, ix, iy, radius=20, out_size=200, zoom=4):
		"""Show a magnified patch centered at (ix,iy) in original image coords."""
		if self.image is None:
			return
		w, h = self.image.size
		# crop box in original coords
		x1 = max(0, ix - radius)
		y1 = max(0, iy - radius)
		x2 = min(w, ix + radius)
		y2 = min(h, iy + radius)
		try:
			patch = self.image.crop((x1, y1, x2, y2))
		except Exception:
			return
		# resize to out_size
		pw, ph = patch.size
		if pw == 0 or ph == 0:
			return
		patch = patch.resize((int(out_size), int(out_size)), Image.NEAREST)
		self._mag_photo = ImageTk.PhotoImage(patch)
		# ensure mag_win exists and is valid; create placeholder if needed
		if not self.mag_win or not hasattr(self.mag_win, 'winfo_exists') or not self.mag_win.winfo_exists():
			try:
				self.mag_win = tk.Toplevel(self.master)
				self.mag_win.title('Magnifier')
				self.mag_win.protocol('WM_DELETE_WINDOW', self._on_mag_close)
				# create an empty label first, then update below
				self.mag_label = tk.Label(self.mag_win)
				self.mag_label.pack()
			except Exception:
				# failed to create magnifier window — clear refs and abort
				self.mag_win = None
				self.mag_label = None
				return

		# update existing label only if it exists
		if self.mag_label and hasattr(self.mag_label, 'config'):
			try:
				self.mag_label.config(image=self._mag_photo)
			except Exception:
				# updating failed (widget possibly destroyed), try to recreate once
				try:
					if self.mag_win and hasattr(self.mag_win, 'destroy'):
						self.mag_win.destroy()
				except Exception:
					pass
				self.mag_win = None
				self.mag_label = None
				# attempt recreate
				try:
					self.mag_win = tk.Toplevel(self.master)
					self.mag_win.title('Magnifier')
					self.mag_win.protocol('WM_DELETE_WINDOW', self._on_mag_close)
					self.mag_label = tk.Label(self.mag_win, image=self._mag_photo)
					self.mag_label.pack()
				except Exception:
					self.mag_win = None
					self.mag_label = None


	def _on_mag_close(self):
		# user closed magnifier window
		self.magnifier_on = False
		if self.mag_win and hasattr(self.mag_win, 'winfo_exists') and self.mag_win.winfo_exists():
			try:
				self.mag_win.destroy()
			except Exception:
				pass
		self.mag_win = None
		self.mag_label = None

	def clear_canvas(self):
		self.canvas.delete('all')
		self.photo = None

	def prev_image(self):
		if self.idx > 0:
			self.idx -= 1
			self.load_current_image()

	def next_image(self):
		if self.idx < len(self.images) - 1:
			self.idx += 1
			self.load_current_image()

	def on_button_press(self, event):
		self._start_x = event.x
		self._start_y = event.y
		self._rect_id = self.canvas.create_rectangle(self._start_x, self._start_y, event.x, event.y, outline='red', width=2)

	def on_move(self, event):
		if self._rect_id is not None:
			self.canvas.coords(self._rect_id, self._start_x, self._start_y, event.x, event.y)

	def on_button_release(self, event):
		if self._rect_id is None:
			return
		x1, y1, x2, y2 = self.canvas.coords(self._rect_id)
		# map back to original image coords
		ox1 = int(round(x1 / self.scale))
		oy1 = int(round(y1 / self.scale))
		ox2 = int(round(x2 / self.scale))
		oy2 = int(round(y2 / self.scale))
		if abs(ox2 - ox1) < 5 or abs(oy2 - oy1) < 5:
			self.canvas.delete(self._rect_id)
			self._rect_id = None
			return
		# normalize order
		left, right = min(ox1, ox2), max(ox1, ox2)
		top, bottom = min(oy1, oy2), max(oy1, oy2)
		# points as four corners (tl,tr,br,bl)
		pts = [[left, top], [right, top], [right, bottom], [left, bottom]]
		# ask for label
		label = simpledialog.askstring('Label', 'Enter label for this box:')
		if label is None:
			# cancel
			self.canvas.delete(self._rect_id)
			self._rect_id = None
			return
		# keep rect id, store annotation
		rect_id = self._rect_id
		self.annotations.append({'label': label, 'points': pts, 'rect_id': rect_id})
		self._rect_id = None
		self.refresh_listbox()

	def _draw_rect_on_canvas(self, pts):
		# pts are in original image coords
		x1, y1 = int(round(pts[0][0] * self.scale / self.scale)), int(round(pts[0][1] * self.scale / self.scale))
		# compute scaled coords properly
		left = int(round(pts[0][0] * self.scale))
		top = int(round(pts[0][1] * self.scale))
		right = int(round(pts[2][0] * self.scale))
		bottom = int(round(pts[2][1] * self.scale))
		return self.canvas.create_rectangle(left, top, right, bottom, outline='green', width=2)

	def refresh_listbox(self):
		self.listbox.delete(0, tk.END)
		for i, a in enumerate(self.annotations):
			pts = a['points']
			self.listbox.insert(tk.END, f"{i+1}. {a['label']} -> {pts}")

	def undo(self):
		if not self.annotations:
			return
		last = self.annotations.pop()
		rid = last.get('rect_id')
		if rid:
			try:
				self.canvas.delete(rid)
			except Exception:
				pass
		self.refresh_listbox()

	def save_json(self):
		if not self.current_image_path:
			messagebox.showinfo('Info', 'No image loaded')
			return
		scene_name = self.scene_var.get() or ''
		ann_out = []
		for a in self.annotations:
			ann_out.append({'label': a['label'], 'points': a['points']})
		data = {
			'image': os.path.basename(self.current_image_path),
			'scene_name': scene_name,
			'annotations': ann_out
		}
		out_path = os.path.splitext(self.current_image_path)[0] + '_scene.json'
		with open(out_path, 'w', encoding='utf-8') as f:
			json.dump(data, f, ensure_ascii=False, indent=2)
		messagebox.showinfo('Saved', f'Saved {out_path}')


def main():
	root = tk.Tk()
	app = SceneAnnotator(root)
	root.mainloop()


if __name__ == '__main__':
	main()

