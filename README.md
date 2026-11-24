# jaydonchua8.github.io

My portfolio site, an interactive dithered chessboard. It's live at https://jaydonchua8.github.io.

- Move your cursor to light up the board. Anything the light doesn't reach stays dark.
- Drag a piece to move it. Each piece only moves the way it does in chess.
- Click a piece to knock it over and open its section, then lift it to go back.
- Click the bunny.

## How it's made

The chess pieces are 3D models built from signed distance fields and ray-marched offline in Python with NumPy. The renderer saves a shade map of each piece standing up and tipped over at many angles, and the page dithers those maps at runtime with an 8x8 Bayer matrix, so the whole site is two colors. Toppling and rocking run on rigid-body physics over those frames.

The page itself is one HTML file with no libraries. The board, the spotlight, the labels and the physics are all drawn on a canvas at pixel scale, and the only outside request is the Lora font.

## Rebuild

```
pip install numpy scipy pillow
python source/build/render_all.py   # renders the pieces into source/build/out/
python source/build/assemble.py     # writes index.html and atlas.png at the repo root
```

The visual style is inspired by Damian Panes's portfolio.
