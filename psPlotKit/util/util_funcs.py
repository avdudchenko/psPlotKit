import os


def create_save_location(working_dir, save_folder):
    if working_dir == None:
        working_dir = os.getcwd()
    if save_folder == None:
        working_dir = os.path.join(working_dir, "figs")
    else:
        working_dir = os.path.join(working_dir, save_folder)
    if os.path.exists(working_dir) == False:
        os.mkdir(working_dir)
    return working_dir


def get_workdir():
    return os.getcwd()
