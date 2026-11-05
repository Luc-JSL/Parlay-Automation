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

// Returns true if the given player has three in a row.
bool hasWon(char board[3][3], char player) {
    for (int i = 0; i < 3; i++) {
        // Check row i and column i.
        if (board[i][0] == player && board[i][1] == player && board[i][2] == player) return true;
        if (board[0][i] == player && board[1][i] == player && board[2][i] == player) return true;
    }
    // Check both diagonals.
    if (board[0][0] == player && board[1][1] == player && board[2][2] == player) return true;
    if (board[0][2] == player && board[1][1] == player && board[2][0] == player) return true;
    return false;
}

int main() {
    char board[3][3];

    // Fill each cell with its number (1-9) so the players can see which cell is which.
    char label = '1';
    for (int row = 0; row < 3; row++) {
        for (int col = 0; col < 3; col++) {
            board[row][col] = label++;
        }
    }

    char player = 'X';  // X always goes first.
    int moves = 0;

    while (true) {
        printBoard(board);

        // Ask the current player which cell they want.
        int cell;
        cout << "Player " << player << ", which cell do you want to go in (1-9)? ";
        while (true) {
            if (!(cin >> cell)) {
                cin.clear();
                cin.ignore(1000, '\n');
                cout << "Please enter a number from 1 to 9: ";
                continue;
            }
            if (cell < 1 || cell > 9) {
                cout << "Please enter a number from 1 to 9: ";
                continue;
            }
            // Convert the cell number (1-9) into a row and column (0-2).
            int r = (cell - 1) / 3;
            int c = (cell - 1) % 3;
            if (board[r][c] == 'X' || board[r][c] == 'O') {
                cout << "That cell is already taken. Pick another: ";
                continue;
            }
            break;
        }

        int row = (cell - 1) / 3;
        int col = (cell - 1) % 3;
        board[row][col] = player;
        moves++;

        if (hasWon(board, player)) {
            printBoard(board);
            cout << "Player " << player << " wins!\n";
            break;
        }

        if (moves == 9) {
            printBoard(board);
            cout << "It's a draw!\n";
            break;
        }

        // Switch to the other player.
        player = (player == 'X') ? 'O' : 'X';
    }

    return 0;
}
