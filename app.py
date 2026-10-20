import tkinter as tk

from gif2mp4.ui import GifToMp4App


def main() -> None:
    root = tk.Tk()
    root.title("Conversor de GIF para MP4")
    root.minsize(760, 480)
    GifToMp4App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
