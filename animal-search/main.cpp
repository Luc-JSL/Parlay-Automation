// Animal Search: linear search vs. binary search on a list of animal names.
#include <algorithm>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using namespace std;

// Removes whitespace (spaces, tabs, Windows '\r') from both ends of a string.
string trim(const string& s) {
    const string ws = " \t\r\n";
    size_t start = s.find_first_not_of(ws);
    if (start == string::npos) return "";
    size_t end = s.find_last_not_of(ws);
    return s.substr(start, end - start + 1);
}

// 1. Reads the file and stores each animal name in a vector.
vector<string> readAnimals(const string& fileName) {
    vector<string> animals;
    ifstream inFile(fileName);
    if (!inFile) {
        cout << "Error: could not open " << fileName << endl;
        return animals;
    }
    string line;
    while (getline(inFile, line)) {
        line = trim(line);
        if (!line.empty()) animals.push_back(line);
    }
    inFile.close();
    return animals;
}

// 2. Prompts the user for an animal name and returns it.
string getAnimalName() {
    string name;
    cout << "Enter an animal name: ";
    getline(cin, name);
    return trim(name);
}

// 3. Linear search: checks each element in order, counting comparisons.
int linearSearch(const vector<string>& animals, const string& target) {
    int tries = 0;
    for (size_t i = 0; i < animals.size(); i++) {
        tries++;
        if (animals[i] == target) {
            cout << "I found " << target << " with a linear search at position "
                 << i << " after " << tries << " tries." << endl;
            return static_cast<int>(i);
        }
    }
    cout << "I could not find " << target << ".  I tried " << tries
         << " animals." << endl;
    return -1;
}

// 4. Binary search: the vector must be sorted. Each loop halves the range,
//    and each check of the middle element counts as one comparison.
int binarySearch(const vector<string>& animals, const string& target) {
    int tries = 0;
    int low = 0;
    int high = static_cast<int>(animals.size()) - 1;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        tries++;
        if (animals[mid] == target) {
            cout << "I found " << target << " with a binary search at position "
                 << mid << " after " << tries << " tries." << endl;
            return mid;
        } else if (animals[mid] < target) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    cout << "I could not find " << target << ".  I tried " << tries
         << " animals." << endl;
    return -1;
}

int main() {
    vector<string> animals = readAnimals("animals.txt");
    if (animals.empty()) return 1;
    cout << "Loaded " << animals.size() << " animals." << endl;

    // Binary search only works on sorted data, and the file is not in perfect
    // order, so make a sorted copy for it.
    vector<string> sortedAnimals = animals;
    sort(sortedAnimals.begin(), sortedAnimals.end());

    string name = getAnimalName();
    linearSearch(animals, name);
    binarySearch(sortedAnimals, name);

    // Keeps the console window open when run from VS Code's debugger.
    cout << "\nPress Enter to exit...";
    cin.get();
    return 0;
}
