import sqlite3

def add_coding_questions():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    questions = [
        ("Python Programming", "Write a Python function `reverse_string(s)` to reverse a string without using slicing [::-1].", "def reverse_string(s):\n    rev = ''\n    for char in s:\n        rev = char + rev\n    return rev", "python, loops, string manipulation, def, return, for"),
        ("Python Programming", "Write a Python script that reads a list of numbers and returns the maximum value without using the built-in max() function.", "def get_max(nums):\n    highest = nums[0]\n    for n in nums:\n        if n > highest:\n            highest = n\n    return highest", "python, iterating, array, loop, comparison, def, return"),
        ("JavaScript Algorithms", "Write a JavaScript function `filterEvens(arr)` to filter out all odd numbers from an array and return a new array.", "function filterEvens(arr) {\n    return arr.filter(n => n % 2 === 0);\n}", "javascript, array, filter, functions, module, function, return"),
        ("JavaScript Algorithms", "Write a JavaScript function `findDuplicates(arr)` that returns an array of duplicate elements in the given array.", "function findDuplicates(arr) {\n    const seen = new Set();\n    const duplicates = new Set();\n    for (let current of arr) {\n        if (seen.has(current)) duplicates.add(current);\n        seen.add(current);\n    }\n    return Array.from(duplicates);\n}", "javascript, array, seen, set, duplicates, loop, algorithms, functions")
    ]
    
    c.executemany("INSERT INTO Questions (topic, question_text, expected_answer, required_skills) VALUES (?,?,?,?)", questions)
    conn.commit()
    conn.close()
    print("New coding technical questions successfully added to the database!")

if __name__ == '__main__':
    add_coding_questions()
