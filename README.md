# Map Editor

Map editor with support for multi-layer editing, custom textures, and a preset system.

## Features

- **Multi-layer editing** - create and manage multiple map layers
- **Support for custom textures** - upload your PNG images
- **Saving in JSON** - fully save all layers and settings
- **Export to PNG** - save the map as an image with x4 scaling
- **Presets system** - save and load ready-made map templates
- **Undo/Redo** - up to 100 steps of history
- **Border editing** - create fences and borders between cells
- **Fill and eyedropper** - quickly copy and fill textures
- **Grid** - convenient navigation on the map

## Instructions for use

### Getting Started

1. **Launch the application** `MapEditor.exe` or `python main.py`
2. The editor window will open with an empty 100×50 map

### Toolbar (top)

- Empty - deletes the texture (puts an empty cell)
- Border - draws/deletes borders between cells
- Eeedropper - copies the texture from the map (Alt+LMB)
- Fill - fills the area with the selected texture
- Texture - selects the texture to draw

### Layer panel

#### Layer switching
- **Up/Down arrows** or enter the layer number in the field
- **Layer list** - opens the layer management dialog for all layers

#### Layer buttons
- **`+`** - Add a new layer (maximum 383)
- **`-`** - Delete the current layer (cannot delete the last one)
- **View** - Hide/show the current layer

#### Layer management dialog
- **Double-click** - switch to the selected layer
- **View** - hide/show the selected layer
- **Delete selected layer** - delete the layer with confirmation

### Action bar (bottom)

#### Saving and loading

- `.png` - export map to image
- `.json` - save project to file
- `.json` - load project from file

#### History
- **↩️** - Undo last action
- **↪️** - Repeat undone action

#### Textures
- **add files** - Load PNG textures
- **remove files** - Delete loaded textures

#### Presets
- **Load preset** - Load a ready-made map template
- **Save preset** - Save the current map as a template

#### Brush
- **`-`** / **`+`** - Reduce/increase the brush size (1-10)
- **Number** - Current brush size

#### Grid
- **Grid** - Enable/disable the grid display

### Map editing

#### Drawing with texture
1. Select a texture from the toolbar
2. Click the LMB on the cell to draw
3. Hold down the LMB and drag to draw a line
4. The brush size can be changed in the action bar

#### Drawing borders
1. Click the **"Border"** button
2. Click on the edge of the cell to create/delete a border
3. Borders are displayed as black lines

#### Using the eyedropper
- **Method 1:** Click the **"Pipette"** button, then click on the texture
- **Method 2:** Press `Alt` and click with the left mouse button on the texture

#### Fill area
1. Select the texture (brush)
2. Click the **"Fill"** button
3. Click on the area to fill
4. All adjacent cells with the same texture are filled

#### Cleaning
- **Clears the current layer
- **Confirmation** - Clears all layers

### Working with textures

#### Loading textures
1. Click **"add files"**
2. Select PNG files in the dialog box
3. The textures will appear in the toolbar
4. The textures are automatically numbered from 1

#### Deleting textures
1. Click **"remove files"**
2. Select the textures to delete (you can select multiple)
3. Click **"Delete selected"** or **"Delete all"**
4. The toolbar will update automatically

### Working with presets

#### Saving a preset
1. Click **"Save preset"**
2. Enter a name (letters, numbers, spaces, `_` and `-`)
3. The preset will be saved in the `assets/presets/` folder

#### Loading a preset
1. Click **"Download preset"**
2. Select a preset from the list
3. Press **"Select"** or **double click**
4. The map will load (the current state will be saved in the history)

#### Removing a preset
1. Press **"Download preset"**
2. Select a preset from the list
3. Press **"Delete"**
4. Confirm the deletion

### File formats

#### JSON project
- Saves all layers, borders, and settings
- Use to save your work
- Format: plain text (can be edited manually)

#### PNG export
- Exports the map to an image
- Scale ×4 for better quality
- Saves:
  - All visible layers
  - Borders (black lines)
  - Grid (if enabled)

### System Requirements

- **OS:** Windows 7/8/10/11
- **Python:** 3.8+ (for running from source)
- **RAM:** 256 MB (512 MB recommended for large maps)
- **Screen:** 1280×720 or larger
- **Dependencies:** Pillow (for image processing)

### License and Distribution

You are free to:
- Use for personal and commercial purposes
- Modify the source code
- Distribute copies

It is prohibited:
- Pass the program off as your own
- Remove information about the author
