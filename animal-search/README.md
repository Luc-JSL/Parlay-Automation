# Animal Search (VS Code)

Reads `animals.txt`, asks for an animal name, then searches for it with a
linear search and a binary search, printing how many comparisons each took.

## Requirements
- VS Code with the **C/C++** extension (Microsoft)
- A g++ compiler on your PATH
  - Windows: MinGW-w64 (e.g. via MSYS2), which also gives you `gdb`
  - macOS: `xcode-select --install`
  - Linux: `sudo apt install g++ gdb`

## Use it
1. In VS Code choose **File > Open Folder...** and open this `animal-search` folder
   (the folder itself, so `animals.txt` is found).
2. **Run:** Terminal > Run Task... > **Run Animal Search**. It builds and runs in the
   terminal; type an animal name and press Enter.
3. **Build only:** `Ctrl+Shift+B` (`Cmd+Shift+B` on Mac).
4. **Debug:** press `F5` (uses "Debug Animal Search").
