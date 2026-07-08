import nbformat
nb = nbformat.read('etl/01_etl_experimentacion.ipynb', as_version=4)
for i, cell in enumerate(nb.cells):
    if cell.cell_type == 'markdown':
        print(f"Cell {i} (Markdown): {cell.source.splitlines()[0]}")
    elif cell.cell_type == 'code':
        source_lines = cell.source.splitlines()
        snippet = source_lines[0] if source_lines else ""
        print(f"Cell {i} (Code): {snippet[:60]}")
