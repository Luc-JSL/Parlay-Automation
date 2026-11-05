#include <iostream>
using namespace std;

// Prints the 3x3 board to the console.
void printBoard(char board[3][3]) {
    cout << "\n";
    for (int row = 0; row < 3; row++) {
        cout << " " << board[row][0] << " | " << board[row][1] << " | " << board[row][2] << "\n";
        if (row < 2) {
            cout << "---+---+---\n";
        }
    }
    cout << "\n";
}

int main() {
    char board[3][3];

    // Fill each cell with its number (1-9) so the user can see which cell is which.
    char label = '1';
    for (int row = 0; row < 3; row++) {
        for (int col = 0; col < 3; col++) {
            board[row][col] = label++;
        }
    }

    printBoard(board);

    // Ask which symbol to place.
    char symbol;
    cout << "Do you want to place X or O? ";
    cin >> symbol;
    symbol = toupper(symbol);
    while (symbol != 'X' && symbol != 'O') {
        cout << "Please enter X or O: ";
        cin >> symbol;
        symbol = toupper(symbol);
    }

    // Ask which cell to go in.
    int cell;
    cout << "Which cell do you want to go in (1-9)? ";
    while (!(cin >> cell) || cell < 1 || cell > 9) {
        cin.clear();
        cin.ignore(1000, '\n');
        cout << "Please enter a number from 1 to 9: ";
    }

    // Convert the cell number (1-9) into a row and column (0-2).
    int row = (cell - 1) / 3;
    int col = (cell - 1) % 3;
    board[row][col] = symbol;

    printBoard(board);

    return 0;
}
