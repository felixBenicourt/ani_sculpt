name = "ani_sculpt"
version = "1.0.0"
author = "felix benicourt"

description = "Custom sclupt on animated meshes"

build_command = False
requires = []

def commands():
    env.PYTHONPATH.append(this.root)
    env.PYTHONPATH.append("{root}/ani_sculpt")

