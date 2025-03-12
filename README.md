## Z3 Wordle Solver

A Wordle puzzle solver using the Z3 theorem prover and Norvig's strategy.

### Installation

```
pip install z3-solver requests
```

### Usage

The solver supports three different game modes:

#### 1. Daily Mode

Solve the daily Wordle puzzle.

```
python wordle_api_solver_nltk.py
```
or
```
python wordle_api_solver_nltk.py --mode daily
```

#### 2. Random Mode

Solve a random Wordle puzzle. You can optionally specify a seed for reproducible results.

```
python wordle_api_solver_nltk.py --mode random
```
or with a specific seed:
```
python wordle_api_solver_nltk.py --mode random --seed 42
```

#### 3. Word Mode

Solve a Wordle puzzle with a specific target word.

```
python wordle_api_solver_nltk.py --mode word --target hello
```

### How It Works

The solver uses the Z3 theorem prover to find the optimal next guess based on the feedback from previous guesses. It starts with Peter Norvig's strategy of using four specific words as the initial guesses, then uses Z3 to find the remaining guesses.