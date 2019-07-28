from enum import Enum, auto
import tkinter

from functools import partial

from pathlib import Path

import os

class FileType(Enum):
    DIRECTORY = "DIRECTORY"
    FILE = "FILE"

    def from_filename(filename):
        # return filetype given filename
        pass

    def get_icon(self):
        return Icons[self.value]


class Item:
    def __init__(self, root, row, filename, filetype):
        self.root = root
        self.row = row
        self.filename = filename
        self.filetype = filetype

        self.label = ItemLabel(root, filename, filetype)

        # Grid
        self.label.grid(row=row, column=0, sticky="w")

    def destroy(self):
        # destroy icon and label
        self.label.destroy()


class ItemLabel(tkinter.Label):
    # TODO: dont subclass Label. instead: control two labels?
    COLOR_SELECTED = "cyan"
    COLOR_DESELECTED = "white"

    def __init__(self, root, filename, filetype):
        self.icon = tkinter.PhotoImage(data=filetype.get_icon())

        super().__init__(
                root,
                text=filename,
                image=self.icon,
                compound="left",
                bg=ItemLabel.COLOR_DESELECTED
                )

        self.root = root
        self.fm = root.fm

        self.filename = filename
        self.filetype = filetype

        # Events
        self.bind("<Button-1>", self.on_click)
        self.bind("<Double-Button-1>", self.on_doubleclick)

        self.selected = False


    def set_selected(self, val):
        if val == self.selected:
            return

        self.selected = val
        if val:
            self.configure(bg=ItemLabel.COLOR_SELECTED)
        else:
            self.configure(bg=ItemLabel.COLOR_DESELECTED)

    def is_selected(self):
        return self.selected

    def select(self):
        self.set_selected(True)

    def deselect(self):
        self.set_selected(False)

    def on_click(self, event):
        print("inner onclick")
        self.root.select_label(self)

    def on_doubleclick(self, event):
        print("doubleclick")
        if self.filetype == FileType.DIRECTORY:
            self.fm.goto(self.filename, relative=True)
        else:
            # TODO: placeholder
            print("Open:", self.filename)


class SideFrame(tkinter.Frame):
    # TODO: change gray to lighter color

    COLOR = "gray"
    COLOR_SELECTED = "cyan"

    DEFAULT_BOOKMARKS = [
        ("/", "/"),
        ("Applications", "/Applications"),
        ("Downloads", "~/Downloads")
    ]

    def __init__(self, root):
        super().__init__(root, bg=SideFrame.COLOR, width=200)

        self.fm = root.get_fm()

        # TODO: get from config later
        self.labels = []

        for row, (name, pathstr) in enumerate(SideFrame.DEFAULT_BOOKMARKS):
            path = Path(pathstr).expanduser()

            label = tkinter.Label(self, text=name, bg=SideFrame.COLOR, anchor="w")
            label.grid(row=row, column=0, sticky="ew")

            # Hover events
            label.bind("<Enter>", partial(self.on_label_enter, label=label))
            label.bind("<Leave>", partial(self.on_label_leave, label=label))
            label.bind("<Button-1>", partial(self.on_label_click, path=path))

            self.labels.append(label)

    def on_label_enter(self, event, label):
        label.configure(bg=SideFrame.COLOR_SELECTED)

    def on_label_leave(self, event, label):
        label.configure(bg=SideFrame.COLOR)

    def on_label_click(self, event, path):
        self.fm.goto(path)



class NavFrame(tkinter.Frame):
    def __init__(self, root, path):
        super().__init__(root)

        self.fm = root.get_fm()

        # Setup Images
        # TODO: streamline process
        self.home_image = tkinter.PhotoImage(data=Icons["HOME"])
        self.up_image = tkinter.PhotoImage(data=Icons["UP"])
        self.forward_image = tkinter.PhotoImage(data=Icons["FORWARD"])
        self.back_image = tkinter.PhotoImage(data=Icons["BACK"])

        self.forward = tkinter.Button(self, image=self.forward_image, command=self.fm.forward)
        self.back = tkinter.Button(self, image=self.back_image, command=self.fm.back)
        self.up = tkinter.Button(self, image=self.up_image, command=self.fm.up)
        self.home = tkinter.Button(self, image=self.home_image, command=self.fm.goto_home)

        self.pathvar = tkinter.StringVar()
        self.pathvar.set(path)
        self.path_entry = tkinter.Entry(self, width=50, textvariable=self.pathvar)
        self.path_entry.bind("<Return>", self.on_enter)

        self.back.grid(row=0, column=0)
        self.forward.grid(row=0, column=1)
        self.up.grid(row=0, column=2)
        self.home.grid(row=0, column=3)
        self.path_entry.grid(row=0, column=4)

    def set_path(self, path):
        self.pathvar.set(path)

    def on_enter(self, event):
        path = self.pathvar.get()
        if not os.path.isdir(path):
            # TODO: Show error message?
            return

        self.fm.goto(self.pathvar.get())


class FilesFrameCanvas(tkinter.Canvas):
    def __init__(self, root):
        super().__init__(
                root,
                height=400 - root.nav_frame.winfo_height(),
                scrollregion=(0,0, 500, 5000) # TODO what are these numbers?
                )
        self.scrollbar = tkinter.Scrollbar(root, command=self.yview)
        self.scrollbar.grid(row=1, column=2, sticky="ns")
        self.configure(yscrollcommand=self.scrollbar.set)

        self.files_frame = FilesFrame(self, root)
        self.create_window((0,0), window=self.files_frame, anchor='nw')

        self.bind_all("<MouseWheel>", self.on_mousewheel)

    def on_mousewheel(self, event):
        print("mousewheel")
        pass


class FilesFrame(tkinter.Frame):
    # enums
    MOUSE_SINGLE = "single"
    MOUSE_MULTIPLE = "multiple"
    # some drag enum?

    def __init__(self, canvas_parent, root):
        super().__init__(canvas_parent)
        self.canvas_parent = canvas_parent
        self.root = root
        self.fm = root.get_fm()

        self.items = []

        self.mouse_mode = FilesFrame.MOUSE_SINGLE

        self.selected_labels = []

        self.bind("<Button-1>", self.on_click)

        # Right click context menu
        # On OS X, right click is Button2
        self.popup = tkinter.Menu(self, tearoff=0)
        self.popup.add_command(label="New Folder")
        self.popup.add_separator()
        self.popup.add_command(label="Paste here")
        self.popup.add_separator()
        self.popup.add_command(label="Properties")

        self.bind("<Button-2>", self.on_right_click)
        # TODO: for macs
        self.bind("<Control-Button-1>", self.on_right_click)


        self.scrollbar = tkinter.Scrollbar(self)
        # self.scrollbar.pack(side=RIGHT, fill="y")

    def refresh(self, files):
        self.selected_labels = []

        for item in self.items:
            # print("destroying label:", label)
            item.destroy()

        self.items = []

        self.test_icons=[]

        for row, f in enumerate(files):
            filename, filetype = f

            label = Item(self, row, filename, filetype)
            # label.grid(row=row, column=1, sticky="w")
            self.items.append(label)


    def deselect_all(self):
        for label in self.selected_labels:
            label.deselect()
        self.selected_labels = []


    def select_label(self, label):
        if self.mouse_mode == FilesFrame.MOUSE_SINGLE:
            self.deselect_all()

        # for both SINGLE and MULTIPLE
        self.selected_labels.append(label)
        label.select()

    def on_click(self, event):
        print("FilesFrame.on_click()")
        self.deselect_all()

    def on_right_click(self, event):
        print("right click", event.x_root, event.y_root)
        self.popup.post(event.x_root, event.y_root)


class FileManager:
    def __init__(self, root, start_path):
        self.root = root

        self.path = start_path

        # Stores path or paths
        self.clipboard = []

        self.history = [start_path]
        self.history_index = 0

        self.location = ""

        self.show_hidden = False

        # Debug mode, don't perform any file IO
        self.dry_run = True


    """
    File functions
    """
    # paste either from 1) copy clipboard, 2) cut clipboard
    def paste(self):
        # if cut clipboard, call rename instead

        # else paste here
        pass

    # called directly from drag and drop or rename
    # called indirectly through paste() from cut/paste
    def rename(old_path, new_path):
        pass

    def mkdir(path):

        # refresh?
        pass

    def rm(path, safe=True):
        # dont implement real "rm" yet, only move to trash
        pass

    """
    Movement functions
    """

    # goto path
    def back(self):
        # if history index is not 0, subtract 1,
        # get path, run goto (add_to_history=False)
        if self.history_index <= 0 or len(self.history) <= 1:
            print("Cannot go back")
        else:
            self.history_index -= 1
            self.goto(self.history[self.history_index], add_to_history=False)


    def forward(self):
        # if history_index is not last index,
        # add 1 to it, get path, run goto (add_to_history=False)
        if self.history_index + 1 >= len(self.history):
            # do nothing
            print("cannot go forward")
        else:
            self.history_index += 1
            self.goto(self.history[self.history_index], add_to_history=False)

    def goto_home(self):
        self.goto(Path.home())
        # get user home dir, goto
        pass

    def goto(self, path, add_to_history=True, relative=False):
        # set new path

        if relative:
            self.path = Path(os.path.join(self.path, path))
        else:
            # TODO is Path(...) necessary here? check where goto is called
            self.path = Path(path)

        # if add_to_history, first remove all entries in history AFTER history_index
        # add to history, set history index to last
        if add_to_history:
            self.history = self.history[:self.history_index + 1]
            self.history.append(self.path)
            self.history_index = len(self.history) - 1
            print("Added to history:", self.path)

        # Set path in navbar
        self.root.nav_frame.set_path(str(self.path))

        # refresh
        self.refresh()

    def up(self):
        # get parent path, goto
        new_path = self.path.parent

        self.goto(new_path)


    """
    UI and miscellaneous?
    """

    def list_dir(self):
        # TODO: fix this
        filenames =  os.listdir(self.path)

        if not self.show_hidden:
            filenames = [f for f in filenames if not f.startswith(".")]

        filenames.sort()

        files = [(f, self.to_filetype(f)) for f in filenames]

        return files

    def to_filetype(self, filename):
        '''
        filename is relative to current path
        '''
        path = os.path.join(self.path, filename)
        if os.path.isdir(path):
            return FileType.DIRECTORY
        return FileType.FILE

    # mostly called indirectly by some functions
    # also possible to add button to call directly?
    def refresh(self):
        '''
        1. Reload fles from path
        2. Triggers parent (FilesFrame) refresh
        '''

        # reload files from path
        files = self.list_dir()

        # TODO: getter instead?
        self.root.files_frame.refresh(files)

        # do you upload path bar here?
        pass

    def get_info(self):
        # maybe show string?
        # filesize, permissions/owners, timestamp?
        return {
            "name": "",
            "path": "",
            "created_at": "",
            "updated_at": "",
            "size": 0,
        }

    def filesize(self):
        # not sure what to return: string or int
        pass

    def set_show_hidden(self, val):
        self.show_hidden = val

        # refresh

    def toggle_show_hidden(self):
        self.set_show_hidden(not self.show_hidden)
        self.refresh()

    # open file
    def open(self):
        pass

    def open_terminal(self):
        pass

###

class Tkfm(tkinter.Tk):
    def __init__(self):
        super().__init__()

        # TODO: use Path.cwd() or config file?
        starting_path = Path.home()

        self.fm = FileManager(self, starting_path)

        # UI

        # Top nav frame
        self.geometry('{}x{}'.format(800, 400))
        self.nav_frame = NavFrame(self, str(starting_path))
        self.nav_frame.grid(row=0, column=0, columnspan=2, sticky="w")
        self.nav_frame.update()

        # Side frame
        self.side_frame = SideFrame(self)
        self.side_frame.grid(row=1, column=0, sticky="nsew")

        # Files frame
        # Create canvas and scrollbar
        self.files_frame_canvas = FilesFrameCanvas(self)
        self.files_frame_canvas.grid(row=1,column=1, sticky="w")
        self.files_frame = self.files_frame_canvas.files_frame

        # Let files frame expand to available space
        self.grid_columnconfigure(1, weight=1)

        # Refresh fm after UI is done. TODO: maybe better workflow?
        self.fm.refresh()

        self.files_frame.update()
        self.files_frame_canvas.config(scrollregion=self.files_frame_canvas.bbox("all"))

        # Keyboard Shortcuts
        self.bind('<Command-g>', lambda _: self.fm.toggle_show_hidden())
        self.bind('<Command-q>', self.quit)


        # HACK, doesnt play well with popup menus
        # self.attributes('-topmost',True)
        # self.after_idle(self.on_idle)
        self.lift()
        self.update()

    def get_fm(self):
        return self.fm


    def quit(self, event):
        self.quit()

    # def on_idle(self):
        # self.attributes("-topmost", False)



Icons = {
    "HOME": "R0lGODlhIAAgAPYAAAAAAGZmZnV1dXt8eqYCAqsEBK8MDLMMDLgPD7UUE70UE7MYFroYF7MZGboZGbMiIrYoJ7guKrk1Nbo4OMAWFsQbG8sdHdUfH9keHs4jI8cpKc0rK9QlJdskJN81Nds/P+QmJuonJ+coKO0qKvA0NPA7O45VVb5IR6llZcBNScFTU+lDQ+9OTvFDQ/JLS+ZUVOhRUe9fX/JUVPNbW8ZgYMZxcMp3d8t4ePNjY/Rra/Vzc/V6en6Ae9fCC4yIU4uIWIiIc4KEfTRlpDxrqEVyq1N9smKIuWuOvW2QvXOVwXubxISGgYaJg4iLhZaXlZeYlqGhoaeopry8vMyGg8+XltWjo9GtrNWxsYCexsbGxc7OztzGxtnLy9PT09zV1dzc3OPc3OTk5Ojm5ufo5+rq6vDw8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAAALAAAAAAgACAAAAf+gACCg4SFhoeIiYMEio2IBQodBY6UggUcLSOSlY0FHi0tIiKbnIcHKy4umaKkpZYOLjKpJSOjoweuAAUbMr0ytCK1HSAdB5OVBR8zyzIkIQoEGCPEHR0Ix40GLzjMJCALU1wRFsLVCtiIDjE5ODjNFwtWX19dJxXCHBwU6IQFGjkAc8gYcQHClnkIazgYESIfhwr8dH3QoQOgixAVTiD8QqZMmC9UGoBomM8CugIvdlDU0SKEAxsfv4wpQ5PMxysiG2bIYHJQgR1AdZT4ViUMmDBkOpZJSmYMGC4NpDnsqSsoCQwNthhFyrRrU6MSyHHYeewnjhEWJhwNg3RMUrf+TcfIHWNURYUQHTIYEGRgoAIactnGDRyGLtvDbG0wCAFir64LCFB8LUwZsVemhU0swMBIECMBNqE8Gf3EiWkoZAYIWM16gE0BADoTAh0myoDbA3jojhJGQJIkSpQkQQL6ywBEAsZ8yRKkufMmWXoDxyKcuPLjh5J/CbNkSZPmTZpsF3DkiJEiRIZox25I+5juQb77CNKlt5D7+AWE6cK+kP7tQXi3hA89ADGPAPjltx8PyH0UxnfeNcGDeMax1hoYWqDQYBdkhOdheF0gpJyD82hRxIYdfhjeF1p00aIWLXYhYxawZRdiGSquuNGOX0hRoyEBWCikkKoNmcuRSDoCEggAOw==",
    "BACK": "R0lGODlhIAAgAPcAAAAAADJjBDdtAzdvBDl0AzpzBDtzBDpyBTp0BDt0BDt1BDt0BTt1BTt2BDt2BTt3BTx2BDx2BT93CT93Cz95CkJ5DUJ6DkN6EER6EEZ9E0+bBVCdBlGeBlSdDkiAFE6DG06EHFCDHlKgB1OgB1OhB1SjB1WkCFalCFenCVeoCVioCVmqCVmqClqsClutCluuC1yuC1yvC12vC1urDV2wC16xC16xDF6yDF+yDF+zDFmkEFmgFl+qFGC0DGC1DWG1DWG2DWG3DWK3DWO4DmO5DmO6DmS7DmW7DmW8D2CmG2KqG2avHWGwFGe/EFSJIFuMLFyNLlyQLGCXLWSXMWKRNWetImisJWqrKmuqLmmwI22zKm61KHW7Lm2rMG2rMXCtNXGtNnGtN3OuOXOvOnWvPHW3NHawPnu7PWjAEGrEEWzHEmvEFXXMHnOeSHaqQnaoR3eiTXixQXizQHqyQ3yzRn23RH21R3+9Q3+1Sn+1S4G3TIK3T4C6SIG4S4O8S4S6TYS7T4a/TYW9ToO4UIS4UYW5Uoa5U4e7U4a+UIi9U4i/U4m7V4i9VIm/VIq+V4e0WYq7WYq8WIq8Wou9Wou8W4y9W4y/Wo6/Xo6+X4+/YI+/YY61aI60apC/YpO+aYTGQ4jBUInBUorBVIrAVYzAWIzAWo7AXY/AX5XRWZHAZJLAZZPBZ5TBaJTCaJXCapbDa5fDbJjEbpjJaZzJb5rFcJvFcZvGc57Hdp/CfZ/IeKLaa6DOc6LOd6PKfqTLfqTMfqbPf6rfd6nNhqrOh6bHiKvLjKjRgKrVgKzXga3Zgq/bgq3QjK/Qj7Ddg7Heg7Hfg7HSkLLSkrLSlLPTlbTUlbTUlrfWmbnWm7nTnrnXnLrYnrLhhLTkhbXlhbXmhbrWoLzYobzZob7ao8DbpcHbp8HbqMLaqsLcqcPcqsPdq8Tdq8PcrMXdrMTdrcberwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAAALAAAAAAgACAAAAj+AAEIHEiwoMGDCBMqXMiwocOHEBMWiMhQAZQJFBVCaLPuQkaEETidc+fxY0ELxMjZUlfSpMAQ2MDVcpUOg0sADaiYo0YLFit0FwoIHTq0oQI47YTFesUqFTt05caJC6ctm7VqCRg+2HTuFqtVqjphqrTI0J48dOKQCTMtq8IKuK610qQp0yVTlhwlAtTHzhwzYr5Ic4vwQ7FllCBJmmSpFKlRihD54VNHzhgwXqIhQOjgybdcgwgVOsSokahQoO6U0ZKlipUrXbBAm3iQQBRmqfDk0fNHUKAzW5i8cNGCRQoTJDZ0GEb7YAIPnvbsSKKExwwXNG7guFEjRgsVJkSPaOjVHCGFR6d0nFgBw0YPIEKE/MghowWKEhzIM2TwZtYSFzb4MIQRSCBRRBA5xMDCCSP4Ul5CBkzBCxc9EIFEE88404wyySBzjDHA/PJgQgI4scsnR6CRxjZEtThiQgFkIAsqa6jBzYsZSRCJLmx4g2NGC7gRTDc/ZnSAFM8UmdEAICj5kZM3RSnllFQWFBAAOw==",
    "FORWARD": "R0lGODlhIAAgAPcAAAAAADNiBDduAzhvAzt1AzpyBDpzBDpzBTp0BDt0BDt1BDt0BTx0BDx1BDx1BTx2BT11BkF5C0F5DEJ5DUJ6Dk6ZBU+bBVCcBVGeBlKfBlKeB0iAFkuBFkyCGk2CG1CFHVKgB1OgB1SiB1SjB1SjCFWkCFalCFemCFenCVioCVmpCVmqCVioC1mqClqsClutCluuC1ytC1yuC1yvC12vC12wC16xC16xDF6yDF+yDF+zDFuoEGC0DGC1DWG1DWG2DWG3DWK3DWO5DmO6DmS7DmW8D2GkH2KmH2KtGGKwFWe/EGezG1eLI1eLJVmMKVuLLF2NLmicN2qdOWWmJWanJ2irJ2mpK2myIW2zKG6yLG+wL3C1LHW+K26uMHCtNXGtN3OvOXSvO3GxMneyPHawPnm2Pnu7PWjAEGrEEWzDF23HFG/IGHLLGXrSI3KeRneiTnqqSnixQHixQXmzQnqyQnqzQ3qzRHy2RH63RX20R322Rny5QHy4QXy6QH68QX+6RX+5Rn6ySn61SX+1Sn+1S3+4SITJPoC7R4C2TIG3TIG2TYK3T4C7SIG5SoK5TYO6TIO6TYS6TYWvXYO3UIS4UIS4UYW5UoW4U4a5U4a6Uoa6U4a5VIi7V4q2XIu8W4y9XY29Xo60aZS+a5e9cI/CXpHDXpTUVZHAZJLAZJLAZZLAZpbDapzLbZ3Nbp7HdqLdZ6HGfaDJeaLJfqPKfqPLfqTMfqbPf6PQdaTSda7efa7ffa/jfK7gfp/CgKjLhajRgKrUgKzXga3Zgq/bgq/chK3Qi6/RjrDdg7Heg7DRj67NkbLSkrTUlbXVl7XSmbXUmLjVm7jWmrLhhLvYoL3Yor7Zo7/ZpL/apcDapsDbpsLcqcLcqsXdrcfesMffscvgt83iuAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAAALAAAAAAgACAAAAj+AAEIHEiwoMGDCBMqXMiwocOHEA0aiOjQwBMGFBca+PZGQcaEBsB1C/Xg40ED3lxN6zXBZEED3FalMqbMA0QDCHLqzGlAG6pPnmI5g0KgIrRp1KpZu4YNW7ZtoDhtsqTqmRuPDA1EyzNI0aRKljBp0pSJ0iJEgi4lk+QgazM5dvIIIpTIEaRIjxoV0lMnDh1aoyhoZBaGTJw5d/AAYnTo0B8+YqocMTLlFKwOCg0s8/IFzJgye/r4MbMFCQsTIjJcqFAhjC8nCRAaKEbFShctWbBcSRIDxgsXKk6QyGChghdZTWKfnFXBAogSKVzMsIEjB44aL1qgEKFBkCgOGGWLM8cwAoULGjp8BAnyg8cNGSt2kOokQeMsCyFMtJihA8iQIkUQIUQPNyzBChwLZDVLLbb8AkwwwgxzDDJpKFGEEFzcEkUBDRng4Ycg5rIGGmcYggsTArgEAAO6sKGGKa1sEICKK/LSxiulRECjQAxIs0sgEOwoUAPESHGAkAIZ8MEASCbZ5JNQRolkQAA7",
    "UP": "R0lGODlhIAAgAPcAAAAAADp0Azt1Azt2AzpzBDtzBDp0BDt0BDp1BDt1BDt2BDt2BTx0BDx1BD52CT92Cj54CUB3DEB4CkF5C0F4DEF7DUZ9EkZ9E06ZBU+bBU+ZBlCcBVGeBlCaCFGbClOeClOcDEqAF0uBF1CFHleeElOgB1SiB1WjCVamCFenCVipCVmpCVqrClutClyuC1yvC1uqDF2wC1+yDFqgF16pFVyhGV2kGGC0DGC1DWK3DWK4DWO5DmS7DmW8D2a+D2e+D2e/D2GkH2e7FWe8FGi8FWezHGi2HFOIIVeKJleLKFyPKWWXM2STNmGkIGOlImSmJGSmJWWmJWanJmanJ2OoIGirJ2qvJmmpK2qpLGqpLWuqLmyqL26tL2myIm24I3GtNnGtN3KvNnOvOW+yMHS0Nna3NnaxPHawPXi0PHu8O3q5PGjAEGnCEGrDEWrEEWzGEWzGEm3IEm3JEm7JEm/LE3HOFG6dQm+gQXioSnu2Q3qzRHuzRX65Q3+/QH+8Qn20SH61SH+1S3umUIC3SoC2TIO4UIW5U4SxWYi1XIu8XIy9XIy9XY2+XomxYI+3aZW/bJa+bpLBZpfDbJrFcZvFcpzGdJ3HdZ7Gd57Dep/DfJ/IeaDIeKLIfaTLfqXNfqbOf6fPf6jWe6jXe6nXfKbJg6nOhavMi6zPia3Nj6nSgKrVgKzXga3Zgq3agq7agq7bgq/bgq/cgq/ZhrDeg7Hfg7PSlbTTlbXUlrndlrvZnr7enr7en7LghL3Zob7bob3Zor7coMLbqcLcqgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAAALAAAAAAgACAAAAj+AAEIHEiwoMGDCBMqXMiwocOCAx48fJjElIWJDEOQ2gQJAsaEEjAtehLpkICPBhU4soQlihNKdxSgHJhA0CkxWaQEgaJJCYKZAJjYAvRFy5QgNa5cEjFzRK1EZ75smdKkBgkwjyZ8rIBq0p6oU6uS8PAH0YKJATKVIvS16FGrHTQowtPAIYJGtwwF0mMmDJcqVGx8yIABhKQlCRgasPOLUaFBedCQGWOFxgkTJThsmFHpCIOFSIIJ65XLFx81ZbrAWKEiBQpQnzx14nRBIQEHESJQiADMT5oiLl68cNGCRSoDBRIkIEDAIYFdfYzIuIEDxw0ZMVQVQElAlxccOXZ+8OCxIweOVYk/EsCFY0cPIGvWAOmxg1V6jARk6eixxs2bN26s0YMr901EwChD/NBGHHTQEUcbP7xS4EMEiEIEEG7IUUcdcrgBBCwTOheKED6wAcccc8DBhg8ScrdKK7HMQgsvvNAySyytHMAdczz2yCNQQAYp5JBEFmmkQQEBADs=",
    "DIRECTORY": "R0lGODlhIAAgAPcAAAAAAD4+PjxWeUREREdHR0lJSUtLS05OTlBQUFJSUlVVVVdXV1paWl5eXl9fX2JiYmVlZWZmZmlpaWxsbG1tbW5ubm9vb3Nzc3d3d3B0eHh4eHp6en5+fjBeljNhnDVlozRlpDRmpDVmpDVmpTZmpDdnpTZnpjdnpzlnpThopTpopDhppjhppzpppzlqpz1rpjlpqF94mW9/lERupU9zoEpzpU51p0Zyq0VyrEZ0rVR2oV18o1V9slR+tVuJu12LvHGGoHOKpmKIuGSLvWqPvmCMwGeQwmiTw2+UwmmVx2mYzWuazm+dz3GWw3GczHCdz3ieynyfynWgznej0Xei0nii0nmk0n6n1H+o1YCAgIGBgYeHhoeHh4qKio6Ojo6Oj4+Pj4CIkoOPn5CQkJGRkZKSkpOTk5SUlJWVlZaWlpeXl5iYmJmZmZqampubm5ycnJ2dnZ6enp+fn5eboKKioqOjo6SkpKWlpKWlpaampqenp6ioqKmpqaqqqqurq6ysrK2trK2tra6urrCwr7CwsLGxsbOzs7a2tb29vb+/v4anz4Oo0YSp0YCo1YGp1YGp1oSs1oWs14at146v04iu14iv14qv14iu2Imv2Iqv2Yqw2Y2z2Y6z2Y+z2Y+z2o+02Y+02o+12pa215C12pK125O225O23JS23JW23JW33JW43Ja43Ja43Ze53Zq42Ji53Zm53Zm63Zq63pu73pu93Z283py93qC93KC+36fB3qPA4afE4qrF46zG5K3H5LLK47jO6LvR6LzR6LzS6b3S6b7T6b/U6sDAwMHBwcLCwcPDw8TExMXFxM3NzcTY7MXY7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAAALAAAAAAgACAAAAj+AAEIHEiwoMGDCBMqXMiw4cENGCJKlKjB4cEszZYpU4YM2bGPiTZYLKjFkJw4cN64acOGTRsyIwluYEZIUKA/fvjw2cOnzgULFioIHUpB4YVCb1iqSZMGzZmnZuT8CSRIEKFChepMSGgh2Z8+fPTkwWOnDp2zaOvYwZNHDxsJCSUMWsP0jBkyY8CA8cLXi94xZMqc6RIhYQREe4KUWFyChOPHkBmT+DCi8ogVBCH0QaPDVbHPxIgNG016mLDTp4OpDnaLBcEHh/DYyEVr0yZOuHF/2s0blO9QoUbZEuWCoAM8ZWb8itWpufPn0J1zKjUJBsEGgOi8ENaKlPfv4MP+f5cUS9EJggzkfEnxbFWq9/Djy0+FipIjXFEKLrgz54azVwAGKOCAr6hSCSSQ7NJEQQqsEQYPxswi4YQUVnhKJpdk6MsQBSXwhhhCAFPhhLK8wkoqpHiCSYYs9tJDQQiMIQMRvJxyiimeaBLJI41g4eOPQPqoCw4FHUAGEEjUIskVVVDh5JNQRukkLC0UZMAWMRhxBRNcdunll14+YUkIBRXAxQ5FPKHEmmy26WabS0hhQkEEcEBDElZMoeeefPbJpxVOuEbQABzUAAUjiCaq6KKLLnIECgUFkIEKPvxg6aWYZqppDh0YJAAIkIUqaqgiiOBBTKimquqqrLbqakAAOw==",
    "FILE": "R0lGODlhIAAgAPYAAAAAADMzM0tLS0xMTE5OTk9PT1BQUFFRUVJSUlNTU1RUVFVVVVZWVldXV1hYWFlZWVpaWltbW1xcXF1dXWBgYGNjY2RkZGZmZmhoaGpqamtra21tbW9vb3BwcHJycnNzc3Z2dnd3d3p6en19fYCAgIGBgYODg4SEhIaGhoiIiImJiYuLi4yMjI6Ojo+Pj5CQkJKSkpOTk5aWlpmZmZycnJ6enrCwsLGxsbu7u7y8vL29vb6+vr+/v8DAwMHBwcLCwsPDw8TExMbGxsfHx8jIyNra2tvb29zc3N3d3d7e3t/f3+Dg4OHh4eLi4uPj4+Tk5OXl5ebm5ufn5+jo6Onp6erq6uvr6+zs7O3t7e7u7u/v7/Dw8PHx8fLy8vPz8/T09PX19fb29vf39/j4+Pn5+fr6+vv7+/z8/P39/f7+/gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAAALAAAAAAgACAAAAf+gACCg4SFhoeIiYqLgzMzNDU0MzIxLiwpJyUjIiAeHBoYFhaJMmhoaWVppqZnrWavZbFks2MViDFoR0hFUEpKS0zBTcNNTsbGTWMTiDBpSElFUUvATMPHT9jZTsqIL2lJSkZRTDo45jg56eo5PFBPYxKILWi+R1LWTthQ+1H9/lDwEK2gtwTJlCY71ulYyFBHDylRxkRApAINsCRT8vGLIqXjlI8gp4yBgAgFmmpJqDzhkYPhjpcwd/igQmXMA0QmTtpgUgVKPykfaVKpQrRolTEOEJE400RalSg9dMDkQbUqjx9WrIxpgGjEmXw8OU6hWSWrlSto014ZswCRiK/+T5hYkeLjpVUePfL2AIIFyxgFiEKYeQKFyZWxQ89e6ZulseMsYxAg+jC48GEfVfX28MHZRxAtWsYYQNTBjM8mWBIvxpIF9JbXsLeIIYBog+koqFWz1vKai+/fsgcgylCGoxMsVX7g3cz5h/MfQIR04SJGAKILxW9AQX529xYuXbx4+fJFfJfqiCoUr3LcCpC8zaEDmQ9kSHn0hyiQ4fgkS/fW34X3BRhhhAEGGF/gZ8gE+03Rn3vwOUdfEBQSgaCChTxABlAPLsYbeOMRKMYYYhiIISEMjMGhf+/FN98QI5JoonWHJDBGFA76t1gWAYYYhhglXkijIQXcmON/vAkpeGCBBiY4ZCEHlBiGFyQCaeWVWAJ5QCIMdOnll2CG2UAAjJRp5plmBgIAOw=="
}

app = Tkfm()

# hack
while True:
    try:
        app.mainloop()
        break
    except UnicodeDecodeError:
        pass

