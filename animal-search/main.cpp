#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <algorithm>
using namespace std;

// Read the animal names from the file into a vector
vector<string> readFile(string fileName) {
    vector<string> animals;
    ifstream file(fileName);
    string line;

    while (getline(file, line)) {
        // Remove the hidden '\r' at the end of each line
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line != "") {
            animals.push_back(line);
        }
    }
    return animals;
}

// Ask the user for an animal name
string getAnimal() {
    string name;
    cout << "Enter an animal name: ";
    getline(cin, name);
    return name;
}

// Check every animal one at a time
void linearSearch(vector<string> animals, string name) {
    int tries = 0;

    for (int i = 0; i < animals.size(); i++) {
        tries++;
        if (animals[i] == name) {
            cout << "I found " << name << " with a linear search at position "
                 << i << " after " << tries << " tries." << endl;
            return;
        }
    }
    cout << "I could not find " << name << ".  I tried " << tries << " animals." << endl;
}

// Check the middle animal and cut the list in half each time
void binarySearch(vector<string> animals, string name) {
    int tries = 0;
    int low = 0;
    int high = animals.size() - 1;

    while (low <= high) {
        int mid = (low + high) / 2;
        tries++;

        if (animals[mid] == name) {
            cout << "I found " << name << " with a binary search at position "
                 << mid << " after " << tries << " tries." << endl;
            return;
        }
        else if (animals[mid] < name) {
            low = mid + 1;   // look in the right half
        }
        else {
            high = mid - 1;  // look in the left half
        }
    }
    cout << "I could not find " << name << ".  I tried " << tries << " animals." << endl;
}

int main() {
    vector<string> animals = readFile("animals.txt");

    if (animals.size() == 0) {
        cout << "Could not read animals.txt" << endl;
        return 1;
    }

    string name = getAnimal();

    linearSearch(animals, name);

    // Binary search needs the list sorted
    sort(animals.begin(), animals.end());
    binarySearch(animals, name);

    return 0;
}
