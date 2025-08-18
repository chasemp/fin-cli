"""
Analytics module for FinCLI

Provides task statistics, overdue analysis, and digest generation.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from .db import DatabaseManager
from .tasks import TaskManager


class AnalyticsManager:
    """Manages task analytics and digest generation."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.task_manager = TaskManager(db_manager)

    def get_task_counts(self, days_back: int = 30) -> Dict[str, Any]:
        """Get task counts for the specified period."""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Get all tasks from the period
            cursor.execute(
                """
                SELECT
                    id, content, created_at, completed_at, labels, source, due_date
                FROM tasks
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """,
                (cutoff_str,),
            )

            tasks = []
            for row in cursor.fetchall():
                tasks.append(
                    {
                        "id": row[0],
                        "content": row[1],
                        "created_at": row[2],
                        "completed_at": row[3],
                        "labels": row[4].split(",") if row[4] else [],
                        "source": row[5],
                        "due_date": row[6],
                    }
                )

        # Calculate statistics
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        stats = {
            "total_tasks": len(tasks),
            "open_tasks": len([t for t in tasks if not t["completed_at"]]),
            "completed_tasks": len([t for t in tasks if t["completed_at"]]),
            "today": {
                "created": len(
                    [
                        t
                        for t in tasks
                        if self._parse_date(t["created_at"]).date() == today
                    ]
                ),
                "completed": len(
                    [
                        t
                        for t in tasks
                        if t["completed_at"]
                        and self._parse_date(t["completed_at"]).date() == today
                    ]
                ),
            },
            "this_week": {
                "created": len(
                    [
                        t
                        for t in tasks
                        if self._parse_date(t["created_at"]).date() >= week_ago
                    ]
                ),
                "completed": len(
                    [
                        t
                        for t in tasks
                        if t["completed_at"]
                        and self._parse_date(t["completed_at"]).date() >= week_ago
                    ]
                ),
            },
            "this_month": {
                "created": len(
                    [
                        t
                        for t in tasks
                        if self._parse_date(t["created_at"]).date() >= month_ago
                    ]
                ),
                "completed": len(
                    [
                        t
                        for t in tasks
                        if t["completed_at"]
                        and self._parse_date(t["completed_at"]).date() >= month_ago
                    ]
                ),
            },
            "overdue": {
                "3_days": self._get_overdue_tasks(tasks, 3),
                "7_days": self._get_overdue_tasks(tasks, 7),
                "30_days": self._get_overdue_tasks(tasks, 30),
            },
            "due_dates": {
                "overdue": self._get_due_date_overdue_tasks(tasks),
                "due_soon": self._get_due_soon_tasks(tasks, 7),
                "due_today": self._get_due_today_tasks(tasks),
                "total_with_due_dates": len([t for t in tasks if t.get("due_date")]),
            },
            "recurring": self._get_recurring_tasks(tasks),
            "by_label": self._get_tasks_by_label(tasks),
        }

        return stats

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now()

    def _get_overdue_tasks(self, tasks: List[Dict], days_threshold: int) -> List[Dict]:
        """Get tasks that are overdue by the specified number of days (based on creation date)."""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        overdue = []

        for task in tasks:
            if not task["completed_at"]:  # Only open tasks
                created_date = self._parse_date(task["created_at"])
                if created_date < cutoff_date:
                    overdue.append(task)

        return overdue

    def _get_due_date_overdue_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Get tasks that are overdue based on due dates."""
        from .utils import DateParser

        overdue = []
        for task in tasks:
            if not task["completed_at"] and task.get(
                "due_date"
            ):  # Only open tasks with due dates
                if DateParser.is_overdue(task["due_date"]):
                    overdue.append(task)

        return overdue

    def _get_due_soon_tasks(self, tasks: List[Dict], days: int = 7) -> List[Dict]:
        """Get tasks that are due soon (within specified days)."""
        from .utils import DateParser

        due_soon = []
        for task in tasks:
            if not task["completed_at"] and task.get(
                "due_date"
            ):  # Only open tasks with due dates
                if DateParser.is_due_soon(task["due_date"], days):
                    due_soon.append(task)

        return due_soon

    def _get_due_today_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Get tasks that are due today."""
        from .utils import DateParser

        due_today = []
        today = date.today().strftime("%Y-%m-%d")

        for task in tasks:
            if not task["completed_at"] and task.get(
                "due_date"
            ):  # Only open tasks with due dates
                if task["due_date"] == today:
                    due_today.append(task)

        return due_today

    def _get_recurring_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Get tasks that appear to be recurring (have recurring-related labels)."""
        recurring_labels = {
            "recurring",
            "repeat",
            "daily",
            "weekly",
            "monthly",
            "routine",
        }
        recurring = []

        for task in tasks:
            task_labels = set(label.lower() for label in task["labels"])
            if task_labels.intersection(recurring_labels):
                recurring.append(task)

        return recurring

    def _get_tasks_by_label(self, tasks: List[Dict]) -> Dict[str, int]:
        """Get task counts grouped by label."""
        label_counts = {}

        for task in tasks:
            for label in task["labels"]:
                label_lower = label.lower()
                label_counts[label_lower] = label_counts.get(label_lower, 0) + 1

        return dict(sorted(label_counts.items(), key=lambda x: x[1], reverse=True))

    def generate_digest(self, period: str = "weekly", format: str = "text") -> str:
        """Generate a digest report for the specified period."""
        stats = self.get_task_counts(30)  # Get last 30 days for context

        if period == "daily":
            return self._generate_daily_digest(stats, format)
        elif period == "weekly":
            return self._generate_weekly_digest(stats, format)
        elif period == "monthly":
            return self._generate_monthly_digest(stats, format)
        else:
            raise ValueError(f"Unknown period: {period}")

    def _generate_daily_digest(self, stats: Dict[str, Any], format: str) -> str:
        """Generate daily digest."""
        if format == "text":
            return f"""📊 Daily Digest - {date.today().strftime('%Y-%m-%d')}

✅ {stats['today']['completed']} tasks completed today
📝 {stats['today']['created']} new tasks added today
🕗 {len(stats['overdue']['3_days'])} tasks overdue > 3 days
📅 {len(stats['due_dates']['due_today'])} tasks due today
⏰ {len(stats['due_dates']['overdue'])} tasks overdue (due dates)
🔁 {len(stats['recurring'])} recurring tasks flagged

Top labels today:
{self._format_label_summary(stats['by_label'])}"""

        elif format == "markdown":
            return f"""# Daily Digest - {date.today().strftime('%Y-%m-%d')}

## Summary
- ✅ **{stats['today']['completed']}** tasks completed today
- 📝 **{stats['today']['created']}** new tasks added today
- 🕗 **{len(stats['overdue']['3_days'])}** tasks overdue > 3 days
- 📅 **{len(stats['due_dates']['due_today'])}** tasks due today
- ⏰ **{len(stats['due_dates']['overdue'])}** tasks overdue (due dates)
- 🔁 **{len(stats['recurring'])}** recurring tasks flagged

## Top Labels
{self._format_label_summary_md(stats['by_label'])}"""

        elif format == "csv":
            header = ",".join(
                [
                    "Date",
                    "Period",
                    "Total Tasks",
                    "Open Tasks",
                    "Completed Tasks",
                    "Today Created",
                    "Today Completed",
                    "Overdue 3 Days",
                    "Due Today",
                    "Overdue Due Dates",
                    "Recurring Tasks",
                ]
            )
            row = ",".join(
                [
                    date.today().strftime("%Y-%m-%d"),
                    "Daily",
                    str(stats["total_tasks"]),
                    str(stats["open_tasks"]),
                    str(stats["completed_tasks"]),
                    str(stats["today"]["created"]),
                    str(stats["today"]["completed"]),
                    str(len(stats["overdue"]["3_days"])),
                    str(len(stats["due_dates"]["due_today"])),
                    str(len(stats["due_dates"]["overdue"])),
                    str(len(stats["recurring"])),
                ]
            )
            return f"{header}\n{row}"

        return ""

    def _generate_weekly_digest(self, stats: Dict[str, Any], format: str) -> str:
        """Generate weekly digest."""
        if format == "text":
            return f"""📊 Weekly Digest - Week ending {date.today().strftime('%Y-%m-%d')}

✅ {stats['this_week']['completed']} tasks completed this week
📝 {stats['this_week']['created']} new tasks added this week
🕗 {len(stats['overdue']['7_days'])} tasks still open > 7 days
📅 {len(stats['due_dates']['due_today'])} tasks due today
⏰ {len(stats['due_dates']['overdue'])} tasks overdue (due dates)
🔁 {len(stats['recurring'])} recurring tasks flagged as overdue

Top labels this week:
{self._format_label_summary(stats['by_label'])}"""

        elif format == "markdown":
            return f"""# Weekly Digest - Week ending {date.today().strftime('%Y-%m-%d')}

## Summary
- ✅ **{stats['this_week']['completed']}** tasks completed this week
- 📝 **{stats['this_week']['created']}** new tasks added this week
- 🕗 **{len(stats['overdue']['7_days'])}** tasks still open > 7 days
- 📅 **{len(stats['due_dates']['due_today'])}** tasks due today
- ⏰ **{len(stats['due_dates']['overdue'])}** tasks overdue (due dates)
- 🔁 **{len(stats['recurring'])}** recurring tasks flagged as overdue

## Top Labels
{self._format_label_summary_md(stats['by_label'])}"""
        elif format == "csv":
            header = ",".join(
                [
                    "Date",
                    "Period",
                    "Total Tasks",
                    "Open Tasks",
                    "Completed Tasks",
                    "Today Created",
                    "Today Completed",
                    "Overdue 3 Days",
                    "Overdue 7 Days",
                    "Overdue 30 Days",
                    "Recurring Tasks",
                ]
            )
            row = ",".join(
                [
                    date.today().strftime("%Y-%m-%d"),
                    "Weekly",
                    str(stats["total_tasks"]),
                    str(stats["open_tasks"]),
                    str(stats["completed_tasks"]),
                    str(stats["this_week"]["created"]),
                    str(stats["this_week"]["completed"]),
                    str(len(stats["overdue"]["3_days"])),
                    str(len(stats["overdue"]["7_days"])),
                    str(len(stats["overdue"]["30_days"])),
                    str(len(stats["recurring"])),
                ]
            )
            return f"{header}\n{row}"

        return ""

    def _generate_monthly_digest(self, stats: Dict[str, Any], format: str) -> str:
        """Generate monthly digest."""
        if format == "text":
            return f"""📊 Monthly Digest - {date.today().strftime('%Y-%m')}

✅ {stats['this_month']['completed']} tasks completed this month
📝 {stats['this_month']['created']} new tasks added this month
🕗 {len(stats['overdue']['30_days'])} tasks still open > 30 days
📅 {len(stats['due_dates']['due_today'])} tasks due today
⏰ {len(stats['due_dates']['overdue'])} tasks overdue (due dates)
🔁 {len(stats['recurring'])} recurring tasks flagged as overdue

Top labels this month:
{self._format_label_summary(stats['by_label'])}"""

        elif format == "markdown":
            return f"""# Monthly Digest - {date.today().strftime('%Y-%m')}

## Summary
- ✅ **{stats['this_month']['completed']}** tasks completed this month
- 📝 **{stats['this_month']['created']}** new tasks added this month
- 🕗 **{len(stats['overdue']['30_days'])}** tasks still open > 30 days
- 📅 **{len(stats['due_dates']['due_today'])}** tasks due today
- ⏰ **{len(stats['due_dates']['overdue'])}** tasks overdue (due dates)
- 🔁 **{len(stats['recurring'])}** recurring tasks flagged as overdue

## Top Labels
{self._format_label_summary_md(stats['by_label'])}"""

        elif format == "html":
            return f"""<html>
<head>
    <title>Monthly Digest - {date.today().strftime("%Y-%m")}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .label {{ color: #666; }}
    </style>
</head>
<body>
    <h1>Monthly Digest - {date.today().strftime("%Y-%m")}</h1>
    <div class="summary">
        <h2>Summary</h2>
        <ul>
            <li>✅ <strong>{stats["this_month"]["completed"]}</strong> tasks completed this month</li>
            <li>📝 <strong>{stats["this_month"]["created"]}</strong> new tasks added this month</li>
            <li>🕗 <strong>{len(stats["overdue"]["30_days"])}</strong> tasks still open > 30 days</li>
            <li>🔁 <strong>{len(stats["recurring"])}</strong> recurring tasks flagged as overdue</li>
        </ul>
    </div>
    <h2>Top Labels</h2>
    {self._format_label_summary_html(stats["by_label"])}
</body>
</html>"""
        return ""

    def _format_label_summary(self, label_counts: List[tuple]) -> str:
        """Format label summary for text output."""
        if not label_counts:
            return "  No labels found"

        lines = []
        for label, count in list(label_counts.items())[:5]:
            lines.append(f"  #{label}: {count} tasks")

        return "\n".join(lines)

    def _format_label_summary_md(self, label_counts: List[tuple]) -> str:
        """Format label summary for markdown output."""
        if not label_counts:
            return "- No labels found"

        lines = []
        for label, count in list(label_counts.items())[:5]:
            lines.append(f"- **#{label}**: {count} tasks")

        return "\n".join(lines)

    def _format_label_summary_html(self, label_counts: List[tuple]) -> str:
        """Format label summary for HTML output."""
        if not label_counts:
            return "<p><em>No labels found</em></p>"

        lines = ["<ul>"]
        for label, count in list(label_counts.items())[:5]:
            lines.append(f'<li><span class="label">#{label}</span>: {count} tasks</li>')
        lines.append("</ul>")

        return "\n".join(lines)

    def export_csv(self, filename: str = None) -> str:
        """Export analytics data to CSV format."""
        if not filename:
            filename = f"fin-analytics-{date.today().strftime('%Y-%m-%d')}.csv"

        stats = self.get_task_counts(30)

        header = ",".join(
            [
                "Date",
                "Period",
                "Total Tasks",
                "Open Tasks",
                "Completed Tasks",
                "Today Created",
                "Today Completed",
                "Overdue 3 Days",
                "Overdue 7 Days",
                "Overdue 30 Days",
                "Recurring Tasks",
            ]
        )
        row = ",".join(
            [
                date.today().strftime("%Y-%m-%d"),
                "Daily",
                str(stats["total_tasks"]),
                str(stats["open_tasks"]),
                str(stats["completed_tasks"]),
                str(stats["today"]["created"]),
                str(stats["today"]["completed"]),
                str(len(stats["overdue"]["3_days"])),
                str(len(stats["overdue"]["7_days"])),
                str(len(stats["overdue"]["30_days"])),
                str(len(stats["recurring"])),
            ]
        )

        csv_content = f"{header}\n{row}\n"

        # Write to file
        with open(filename, "w") as f:
            f.write(csv_content)

        return filename
