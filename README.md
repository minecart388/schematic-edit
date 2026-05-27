# Schematic-Edit

Multi-layer map editor with support for custom textures, a preset system, a command console, and PNG export.

## Features

- **Multi-layer editing** – create and manage layers (up to 383)
- **Support for custom textures** – load PNG images
- **Save to JSON** – fully save all layers, borders, and settings
- **Export to PNG** – save the map as a image
- **Preset System** – saving and loading ready-made map templates
- **Undo / Redo** – up to 100 steps of history
- **Boundary Editing** – creating fences and borders between cells
- **Fill and Eyedropper** – quickly copying and filling textures
- **Control Console** – drawing shapes, managing layers and presets through text commands
- **Grid** – convenient navigation through the map
- **Hotbar** – quick access to 9 texture slots

## Usage

### Launching

1. Launch the application `Schematic-Edit` (or `main.py` from the source code).
2. The editor window will open with an empty 100×50 map.

### Toolbar (at the top)

- **Eraser** – removes the texture
- **Border** – draws/deletes borders between cells
- **Pipette** – copies a texture from the map
- **Fill** – fills an area with the selected texture
- **Textures** – appear after loading, select a texture to draw
- **Hotbar** – 9 slots for quick access to textures

### console commands

- `help` – show help
- `circle x y radius fill` – draw a circle
- `rect x1 y1 x2 y2 fill` – draw a rectangle
- `line x1 y1 x2 y2 <thickness>` – draw a line
- `clear <all/layer>` – clear all layers or the current layer
- `layers` – show layer information
- `layer <number>` – switch to a layer
- `layer <number> show` - show/hide layer
- `layer <number> del` - delete layer
- `tool` – show the current tool
- `presets` – list of available presets
- `save_preset` – save the current map as a preset
- `load_preset` – load a preset
- `delete_preset <name>` – delete a preset (without the `.json` extension)
- `clear_console` – clear the console

**Options:**
- `fill`: `true` / `false` – fill the shape
- Coordinates `x`, `y` – in the map cells (from 0 to width/height)
- `thickness` – from 1 to 10

### Editing the map

#### Drawing with a texture
1. Select a texture in the toolbar or in the hotbar.
2. Click with the left mouse button on the cell – the texture will be placed.
3. Hold down the left button and drag the mouse to draw a line.
4. You can change the brush size in the action bar.

#### Using the eyedropper
- **Method 1:** Click on the **"Eyedropper"** button, then click on the texture on the map.
- **Method 2:** hold down `Alt` and click on the texture with the left mouse button.

#### Fill area
1. Select the texture (brush).
2. Click on the **"Fill"** button.
3. Click on the area you want to fill.
4. All adjacent cells with the same texture will be replaced.

#### Clear
- **Clear the current layer** - through the console: `clear layer`
- **Clear all layers** – via console: `clear all` or the "Clear" button with confirmation.

### Working with textures

#### Loading textures
1. Click on **"Load textures"** .
2. Select PNG files in the dialog box.
3. The textures will appear in the toolbar, hotbar, and will be available for selection.

#### Deleting textures
1. Click on **"Delete textures"** .
2. A dialog with a list of all loaded textures will open.
3. Enter the numbers to delete (separated by spaces) or `all` to delete all.
4. The toolbar and hotbar will update automatically.

### Working with presets

#### Saving a preset
1. Click on **"Save preset"** or enter `save_preset` in the console.
2. Enter a name (letters, numbers, spaces, `_` and `-`).
3. The preset will be saved in the `assets/presets/` folder.

#### Loading a preset
1. Click on **"Load preset"** or enter `load_preset` in the console.
2. Select a preset from the list (you can enter the name in the console).
3. The map will load (the current state will be saved in the history).

#### Deleting a preset
1. Enter `delete_preset <name>` (without the `.json` extension) in the console.
2. Confirm the deletion.

## System requirements

- **OS:** Windows 7/8/10/11 (also works on Linux/macOS when run from source)
- **Python:** 3.8+ (to run from source)
- **RAM:** 256 MB (512 MB recommended for large maps)
- **Screen:**** 1280×720 or more
- **Dependencies:** Pillow (for image processing)

## License and distribution

Allowed:
- Personal and commercial use
- Modification of the source code
- Distribution of copies

Prohibited:
- Passing off the program as your own
- Removing the author's information