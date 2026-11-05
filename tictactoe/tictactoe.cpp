#include <iostream>
using namespace std;

// Prints the tic tac toe board to the console
void printBoard(char board[3][3])
{
    cout << endl;
    for (int row = 0; row < 3; row++)
    {
        cout << " " << board[row][0] << " | " << board[row][1] << " | " << board[row][2] << endl;
        if (row < 2)
        {
            cout << "---+---+---" << endl;
        }
    }
    cout << endl;
}

// Returns true if the player has three in a row
bool checkWinner(char board[3][3], char player)
{
    // check the rows
    for (int row = 0; row < 3; row++)
    {
        if (board[row][0] == player && board[row][1] == player && board[row][2] == player)
        {
            return true;
        }
    }

    // check the columns
    for (int col = 0; col < 3; col++)
    {
        if (board[0][col] == player && board[1][col] == player && board[2][col] == player)
        {
            return true;
        }
    }

    // check the diagonals
    if (board[0][0] == player && board[1][1] == player && board[2][2] == player)
    {
        return true;
    }
    if (board[0][2] == player && board[1][1] == player && board[2][0] == player)
    {
        return true;
    }

    return false;
}

int main()
{
    char board[3][3] = { {'1', '2', '3'},
                         {'4', '5', '6'},
                         {'7', '8', '9'} };

    char player = 'X';
    int moves = 0;
    bool gameOver = false;

    while (gameOver == false)
    {
        printBoard(board);

        int cell;
        cout << "Player " << player << ", which cell do you want to go in (1-9)? ";
        cin >> cell;

        // turn the cell number into a row and column
        int row = (cell - 1) / 3;
        int col = (cell - 1) % 3;

        // make sure the cell is a real cell and is not already taken
        while (cell < 1 || cell > 9 || board[row][col] == 'X' || board[row][col] == 'O')
        {
            cout << "That cell is not available. Pick another one: ";
            cin >> cell;
            row = (cell - 1) / 3;
            col = (cell - 1) % 3;
        }

        board[row][col] = player;
        moves++;

        if (checkWinner(board, player) == true)
        {
            printBoard(board);
            cout << "Player " << player << " wins!" << endl;
            gameOver = true;
        }
        else if (moves == 9)
        {
            printBoard(board);
            cout << "It's a draw!" << endl;
            gameOver = true;
        }
        else
        {
            // switch players
            if (player == 'X')
            {
                player = 'O';
            }
            else
            {
                player = 'X';
            }
        }
    }

    return 0;
}
