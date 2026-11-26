# Find closing odds for one football match

This notebook checks whether a single fixture has a complete set of closing home, draw and away prices. Run it in a workshop with the included fictional rows, then use a real season to repeat the exercise. [Open in Colab](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/labs/historical-match/closing-odds.ipynb) · [View the notebook](closing-odds.ipynb)

[Download the classroom worksheet and answer key (2-page PDF)](https://raw.githubusercontent.com/JacobiusMakes/parlayapi-notebooks/main/labs/historical-match/match-worksheet.pdf). Print the first page for participants and keep the second for discussion.

1. Run all cells with the default `SOURCE = "practice"`. Two matches share the same teams on different dates. The first is missing its closing draw price.
2. Change `SOURCE` to `"publisher"` and run all cells again. The notebook downloads the 2024/25 English Premier League CSV directly from Football-Data.co.uk and selects Man United at home to Fulham on 16 August 2024.
3. Compare the output to the three Bet365 closing columns in the source row. The report preserves missing prices and flags ambiguous matches. The notebook includes an answer key for the practice exercise.

Football-Data.co.uk publishes the historical CSV and its column definitions. ParlayAPI provides the teaching code and fictional practice rows. [Season downloads](https://www.football-data.co.uk/englandm.php) · [Column definitions](https://www.football-data.co.uk/notes.txt)
