# import json
# import random
# from fastmcp import FastMCP

# # Create the FastMCP server instance
# mcp = FastMCP("Simple Calculator Server")


# # Tool: Add two numbers
# @mcp.tool
# def add(a: int, b: int) -> int:
#     """Add two numbers together.

#     Args:
#         a: First number
#         b: Second number

#     Returns:
#         The sum of a and b
#     """
#     return a + b


# # Tool: Generate a random number
# @mcp.tool
# def random_number(
#     min_val: int = 1,
#     max_val: int = 100
# ) -> int:
#     """Generate a random number within a range.

#     Args:
#         min_val: Minimum value (default: 1)
#         max_val: Maximum value (default: 100)

#     Returns:
#         A random integer between min_val and max_val
#     """
#     return random.randint(min_val, max_val)


# # Resource: Server information
# @mcp.resource("info://server")
# def server_info() -> str:
#     """Get information about this server."""

#     info = {
#         "name": "Simple Calculator Server",
#         "version": "1.0.0",
#         "description": "A basic MCP server with math tools",
#         "tools": ["add", "random_number"],
#         "author": "Your Name"
#     }

#     return json.dumps(info, indent=2)
import sqlite3
import json
from pathlib import Path
from datetime import date

from fastmcp import FastMCP


mcp = FastMCP("Expense Tracker")


BASE_DIR = Path(__file__).resolve().parent

DB_NAME = BASE_DIR / "expenses.db"
CATEGORY_FILE = BASE_DIR / "category.json"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def load_categories():
    """Load categories from category.json."""

    with open(CATEGORY_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data["categories"]


def get_category_names():
    """Return all available category names."""

    categories = load_categories()

    return {
        category["name"].lower()
        for category in categories
    }


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            expense_date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


@mcp.tool
def get_categories() -> list[dict]:
    """Return all available expense categories."""

    return load_categories()


@mcp.tool
def add_expense(
    amount: float,
    category: str,
    description: str = "",
    expense_date: str = ""
) -> dict:
    """Add a new expense."""

    # Validate amount
    if amount <= 0:
        return {
            "success": False,
            "message": "Amount must be greater than 0"
        }

    # Validate category
    category_names = get_category_names()

    if category.lower() not in category_names:
        return {
            "success": False,
            "message": f"Invalid category: {category}",
            "available_categories": sorted(category_names)
        }

    # Use today's date if no date is provided
    if not expense_date:
        expense_date = date.today().isoformat()

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO expenses
        (amount, category, description, expense_date)
        VALUES (?, ?, ?, ?)
        """,
        (
            amount,
            category,
            description,
            expense_date
        )
    )

    conn.commit()

    expense_id = cursor.lastrowid

    conn.close()

    return {
        "success": True,
        "id": expense_id,
        "message": "Expense added successfully"
    }


@mcp.tool
def list_expenses() -> list[dict]:
    """Return all expenses."""

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            id,
            amount,
            category,
            description,
            expense_date
        FROM expenses
        ORDER BY expense_date DESC, id DESC
        """
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@mcp.tool
def get_expense(expense_id: int) -> dict:
    """Get a single expense by ID."""

    conn = get_db()

    row = conn.execute(
        """
        SELECT
            id,
            amount,
            category,
            description,
            expense_date
        FROM expenses
        WHERE id = ?
        """,
        (expense_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return {
            "success": False,
            "message": "Expense not found"
        }

    return {
        "success": True,
        "expense": dict(row)
    }


@mcp.tool
def delete_expense(expense_id: int) -> dict:
    """Delete an expense by ID."""

    conn = get_db()

    cursor = conn.execute(
        "DELETE FROM expenses WHERE id = ?",
        (expense_id,)
    )

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return {
            "success": False,
            "message": "Expense not found"
        }

    return {
        "success": True,
        "message": "Expense deleted"
    }


@mcp.tool
def get_total_expenses() -> dict:
    """Return the total amount spent."""

    conn = get_db()

    row = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        """
    ).fetchone()

    conn.close()

    return {
        "success": True,
        "total": row["total"]
    }


@mcp.tool
def get_expenses_by_category(category: str) -> dict:
    """Return total spending for a specific category."""

    category_names = get_category_names()

    if category.lower() not in category_names:
        return {
            "success": False,
            "message": f"Invalid category: {category}",
            "available_categories": sorted(category_names)
        }

    conn = get_db()

    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(amount), 0) AS total,
            COUNT(*) AS count
        FROM expenses
        WHERE LOWER(category) = LOWER(?)
        """,
        (category,)
    ).fetchone()

    conn.close()

    return {
        "success": True,
        "category": category,
        "total": row["total"],
        "expense_count": row["count"]
    }


# if __name__ == "__main__":
#     init_db()
#     mcp.run()

# Start the server
if __name__ == "__main__":
    init_db()
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )
