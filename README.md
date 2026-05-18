# Map Editor

Multi-layer map editor with support for custom textures, a preset system, a command console, and PNG export.

## Features

- **Multi-layer editing** - create and manage multiple layers (up to 383)
- **Support for custom textures** - upload your PNG images
- **Saving in JSON** - fully save all layers, borders, and settings
- **Export to PNG** – save the map as an image with a scale of ×4
- **Preset System** – save and load ready-made map templates
- **Undo / Redo** – up to 100 steps of history
- **Border Editing** – create fences and borders between cells
- **Fill and Eyedropper** – quickly copy and fill textures
- **Control Console** – draw shapes, manage layers, and presets using text commands
- **Grid** – easily navigate the map
- **Light and dark themes** – one-click switching

## Instructions for use

### Launching

1. Launch the application `map_editor.exe` (or `python main.py` from the source code)
2. The editor window will open with an empty map of 100×50 cells

### Toolbar (top)

- **Void** – removes the texture (puts a blank cell)
- **Border** – draws/removes borders between cells
- **Pipette** – copies the texture from the map (also works `Alt+LMB`)
- **Fill** – fills the area with the selected texture
- **Textures** – select the texture to draw (appear after loading)

### Layer panel

#### Layer switching
- **Up/Down arrows** or enter the layer number in the field
- **Layer list** – opens the dialog for managing all layers

#### Layer buttons
- **`+`** – add a new layer (maximum 383)
- **`-`** – delete the current layer (you cannot delete the last one)
- **View** – hide/show the current layer

#### Layer management dialog
- **Double-click** – switch to the selected layer
- **View** – hide/show the selected layer
- **Delete selected layer** – delete with confirmation

### Action bar (bottom)

#### Saving and loading
- **`.png`** – export the map to an image (scale ×4, takes into account visible layers, borders, and grid)
- **`.json`** – save the project to a file
- **`.json`** – load the project from a file

#### History
- **↩️** – undo the last action
- **↪️** – repeat the undone action

#### Textures
- **Load textures** – add PNG files
- **Delete textures** – delete loaded textures

#### Presets
- **Load preset** – load a ready-made map template
- **Save preset** – save the current map as a template

#### Brush
- **`-`** / **`+`** – reduce/increase the brush size (1–10)
- **Number** – current brush size

#### Grid
- **Grid** – enable/disable grid display

#### Theme
- **Theme** - switch between light and dark themes

### Control console

The console is located on the right and allows you to execute text commands.  
Enter a command and press `Enter`.

#### Basic commands

- `help` - show help
- `circle x y radius fill` - draw a circle
- `square x y size fill` - draw a square
- `rect x1 y1 x2 y2 fill` - draw a rectangle
- `line x1 y1 x2 y2 thickness` - draw a line
- `clear [all\|layer]` - clear all layers or the current one
- `layers` - show layer information
- `layer <number>` - switch to a layer
- `tool` - show the current tool
- `presets` - list of available presets
- `save_preset` - save the current map as a preset
- `load_preset` - load a preset
- `delete_preset <name>` - delete a preset
- `clear_console` - clear the console

**Parameters:**
- `fill`: `true` / `false` – fill the shape
- Coordinates `x`, `y` – in map cells (from 0 to width/height)
- `thickness` – from 1 to 10

### Map editing

#### Drawing with texture
1. Select a texture in the toolbar
2. Click the left mouse button on a cell to draw
3. Hold down the left mouse button and drag to draw a line
4. The brush size can be changed in the action bar

#### Drawing borders
1. Click the **"Border"** button
2. Click on the edge of the cell (between two cells) – the border will be created/deleted
3. Borders are displayed as black lines

#### Using the eyedropper
- **Method 1:** Click the **"Eyedropper"** button, then click on the texture
- **Method 2:** Hold down `Alt` and click with the left mouse button on the texture

#### Fill area
1. Select a texture (brush)
2. Click the **"Fill"** button
3. Click on the area to be filled
4. All adjacent cells with the same texture will be filled

#### Clear
- **Clear the current layer** – through the console: `clear layer`
- **Clear all layers** – through the console: `clear all` or the "Clear" button with confirmation

### Working with textures

#### Loading textures
1. Click on "Load textures"
2. Select PNG files in the dialog box
3. The textures will appear in the toolbar, automatically numbered from 1

#### Deleting textures
1. Click on "Delete textures"
2. A list of available textures will appear in the console
3. Enter the numbers to delete (separated by spaces) or `all` to delete all
4. The toolbar will update automatically

### Working with presets

#### Saving a preset
1. Click **"Save preset"** or enter `save_preset` in the console
2. Enter a name (letters, numbers, spaces, `_` and `-`)
3. The preset will be saved in the `assets/presets/` folder

#### Loading a preset
1. Click **"Load preset"** or enter `load_preset` in the console
2. Select a preset from the list (you can enter the name in the console)
3. The map will load (the current state is saved in the history)

#### Deleting a preset
1. Enter `delete_preset <name>` in the console (without the `.json` extension)
2. Confirm the deletion

### File formats

#### JSON project
- Saves all layers, borders, and settings
- Use to save your work
- Format: plain text (can be edited manually)

#### PNG export
- Exports the map to an image
- Scale ×4 for better quality
- Saves:  - All visible layers  - Borders (black lines)  - Grid (if enabled)

## System requirements

- **OS:** Windows 7/8/10/11 (also works on Linux/macOS when run from source)
- **Python:** 3.8+ (to run from source)
- **RAM:** 256 MB (512 MB recommended for large maps)
- **Screen:**** 1280×720 or more
- **Dependencies:** Pillow (for image processing)

## License and distribution

Allowed:
- Use for personal and commercial purposes
- Modify the source code
- Distribute copies

Prohibited:
- Pass off the program as your own
- Remove information about the author