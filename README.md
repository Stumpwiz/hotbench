# Black History Month Essay Judging System

An automated essay evaluation system using multiple LLM judges to fairly assess middle school student essays for a Black
History Month contest.

## Contest Overview

This system evaluates essays based on the following criteria:

### Requirements

- **Topic**: Essays must focus on one of these historical figures:
    - Gladys West
    - Garrett Morgan
    - Mark Dean
    - Valerie Thompson
    - Langston Hughes
    - Frederick McKinley Jones
    - Marie Van Brittan Brown
    - Lonnie Johnson
    - Dr. Shirley Ann Jackson
    - David Driskell

- **Question**: "What is the most important contribution to society that your chosen individual has made?"
- **Length**: Maximum 400 words

### Evaluation Rubric

Multiple judges evaluate each essay on:

1. **Effectiveness** (1-25 points): Did the student effectively demonstrate the individual's most important contribution
   to society?
2. **Creativity/Originality** (1-25 points): Distinct from being imitative
3. **Scholarship/Craftsmanship** (1-25 points): Organization, sources, design
4. **Effort** (1-10 points): Time invested and attention to detail

**Total possible score**: 85 points per judge, 170 points overall (2 judges currently)

## System Architecture

### Two LLM Judges

The system employs multiple LLM judges, each with unique evaluation perspectives:

1. **Judge 1: The Academic** (GPT-4o-mini): Focuses on scholarly rigor and historical accuracy
2. **Judge 2: The Creative Writer** (Gemini 1.5 Flash): Emphasizes creative expression and originality

Additional judges can be configured in `hotbench/judges.py`.

### Extra LLM - The Meta-Analyzer

After all judges score the essays, an additional LLM (GPT-4) analyzes:

- Common characteristics of winning essays
- Judge consistency and patterns
- Rubric effectiveness
- Developmental insights
- Recommendations for improvement

## Project Structure

```
hotbench/
├── assets/              # Icons and static assets
│   └── icons/           # For later use
├── data/                # Data directory
│   ├── essays/          # Input: Place essay body files here (firstnameLastname.txt)
│   ├── outputs/         # Output: Generated reports and results
│   └── logs/            # Application logs, not currently used
├── hotbench/            # Main package
│   ├── __init__.py
│   ├── judges.py        # Judge definitions and scoring logic
│   ├── llm.py           # LLM evaluation orchestration
│   ├── meta_judge.py    # Meta-analysis by additional LLM
│   ├── models.py        # Data models (Essay, EssayEvaluation, etc.)
│   ├── settings.py      # Configuration and settings
│   └── utils.py         # Utility functions
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables (API keys)
```

## Installation

### Prerequisites

- Python 3.8 or higher
- API keys for:
    - OpenAI (required)
    - Google Gemini (required)
    - LangSmith (optional)
    - Weights & Biases (optional)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd hotbench
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

   Required environment variables:
   ```
   OPENAI_API_KEY=your_openai_key
   GOOGLE_API_KEY=your_google_key
   ```

## Usage

### 1. Prepare Essays

Place essay submissions as text files in the `data/essays/` directory with the naming convention:

```
firstnameLastname.txt
```

Examples:

- `johnDoe.txt`
- `janeDoe.txt`

Remove all header/footer lines to limit word count to essay body only.

### 2. Run the Evaluation

```bash
python main.py
```

The system will:

1. Load environment variables and API keys
2. Discover all essays in `data/essays/`
3. Confirm the number of essays and judges
4. Evaluate each essay with all judges (requires confirmation)
5. Generate individual judge reports
6. Consolidate scores and determine winners
7. Perform meta-analysis

### 3. Review Results

All output files are saved to `data/outputs/`:

- `judge1.txt`, `judge2.txt`, etc. - Individual judge evaluations
- `final_results.txt` - Consolidated scores and rankings
- `judge5.txt` - Meta-analysis by the fifth LLM
- `summary_report.md` - Quick summary table only at this time

## Configuration

### Customizing Settings

Edit `hotbench/settings.py` to configure:

- Number of judges and winners
- Default model names
- Scoring categories and point values
- Paths for data directories

### Adding More Judges

Add judge definitions in `hotbench/judges.py` by:

1. Creating a new judge class (inheriting from `Judge`)
2. Adding the instance to `get_all_judges()` function

Example:

```python
def get_all_judges() -> List[Judge]:
    return [
        OpenAIAcademicJudge(judge_id=1),
        GoogleCreativeJudge(judge_id=2),
        OpenAIAcademicJudge(judge_id=3, model_name="gpt-4"),  # Add more judges
    ]
```

### Customizing the Rubric

Edit `SCORE_CATEGORIES` in `hotbench/utils.py`:

```python
SCORE_CATEGORIES = {
    "effectiveness": 25,
    "creativity": 25,
    "scholarship": 25,
    "effort": 10,
}
```

## Development

### Running Tests

```bash
# Test imports
python -c "from hotbench.settings import settings; from hotbench.llm import EssayEvaluator; print('✓ All imports successful')"
```

### Code Quality

The project follows best practices:

- Type hints throughout
- Pydantic models for data validation
- Centralized configuration with `pydantic-settings`
- Specific exception handling
- Rich console output for better UX

## Output Examples

### Judge Report Format

Each judge provides:

- Scores for each rubric category
- Total score
- Detailed rationale citing specific examples

### Final Results

- Ranked list of all essays
- Winner designations (trophy for first place)
- Score breakdowns by judge
- Detailed per-student analysis

### Meta-Analysis, To Be Added

- Winning essay characteristics
- Judge consistency analysis
- Rubric effectiveness evaluation
- Recommendations for future contests

## Troubleshooting

### Missing API Keys

If you see `Missing required API keys` error:

1. Ensure `.env` file exists in project root
2. See `.env.example` for guidance
3. Add required API keys: `OPENAI_API_KEY`, `GOOGLE_API_KEY`
4. Restart the application

### No Essays Found

If you see `No essays found` warning:

1. Check essays are in `data/essays/` directory
2. Ensure files are named `firstnameLastname.txt`
3. Verify files contain text (not empty)

### Import Errors

If you encounter import errors:

1. Ensure virtual environment is activated
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Verify Python version is 3.8+

## Contributing

Contributions can't be accepted at this time.

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

### Key Points:
- ✅ **Freedom to use** — Use the software for any purpose
- ✅ **Freedom to study** — Access and modify the source code
- ✅ **Freedom to share** — Redistribute copies to help others
- ✅ **Freedom to improve** — Distribute modified versions

### Copyleft Requirements:
- **Share improvements** — If you modify and distribute this software, you must share your changes under the same license
- **Network use provision** — If you run a modified version on a server and let others interact with it, you must make the source code available to those users
- **Attribution required** — You must retain all copyright and license notices

This strong copyleft license ensures the software and all derivatives remain free and open source, even when used to provide services over a network.

For the full license text, see [LICENSE](LICENSE) or https://www.gnu.org/licenses/agpl-3.0.html

**Why AGPL?** This license prevents companies from taking this code, modifying it, and offering it as a proprietary service without contributing back to the community.

## Acknowledgments

This system was designed to provide fair, consistent evaluation of student essays using the power of multiple AI
perspectives, ensuring that each submission receives thorough and unbiased assessment.
