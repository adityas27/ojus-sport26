# CSV Export Scripts for Cultural Events

Two Django management commands to export registrations and teams data to CSV files.

## 1. Export Registrations

**Command:** `export_registrations_csv`

Exports all cultural event registrations to **separate CSV files by event**. Each row represents one participant registration.

### Usage

```bash
python manage.py export_registrations_csv
```

### Options

- `--output-dir` (default: `.`): Specify output directory for CSV files
- `--event` (optional): Export only specific event (e.g., web-design, photography)

### Examples

```bash
# Export all events to current directory
python manage.py export_registrations_csv

# Export to specific directory
python manage.py export_registrations_csv --output-dir ./exports

# Export only specific event
python manage.py export_registrations_csv --event web-design

# Export specific event to custom directory
python manage.py export_registrations_csv --event photography --output-dir ./registrations
```

### Output Format

Creates separate CSV files for each event (e.g., `web-design.csv`, `photography.csv`) with columns:
- `name` - Full name of participant (or username if name not available)
- `event` - Event name
- `phone_number` - Phone number of participant

### Example Output

**web-design.csv:**
```csv
name,event,phone_number
John Doe,Web Design,9876543210
Jane Smith,Web Design,9123456789
Bob Wilson,Web Design,
```

**photography.csv:**
```csv
name,event,phone_number
Alice Johnson,Photography,9111111111
Charlie Brown,Photography,9999999999
```

---

## 2. Export Teams

**Command:** `export_teams_csv`

Exports all team event teams (valorant, paintball) to separate CSV files by event. Each row represents a team member.

### Usage

```bash
python manage.py export_teams_csv
```

### Options

- `--output-dir` (default: `.`): Specify output directory for CSV files
- `--event` (optional): Export only specific event (e.g., valorant, paintball)

### Examples

```bash
# Export all team events to current directory
python manage.py export_teams_csv

# Export to specific directory
python manage.py export_teams_csv --output-dir ./exports

# Export only valorant teams
python manage.py export_teams_csv --event valorant

# Export only paintball teams to custom directory
python manage.py export_teams_csv --event paintball --output-dir ./team_exports
```

### Output Format

Creates separate CSV files for each event (e.g., `valorant.csv`, `paintball.csv`) with columns:
- `team_name` - Name of the team
- `leader_name` - Full name of team leader (or username if name not available)
- `leader_phone` - Phone number of team leader
- `member_name` - Full name of team member
- `member_phone` - Phone number of team member
- `event` - Event name

### Example Output

**valorant.csv:**
```csv
team_name,leader_name,leader_phone,member_name,member_phone,event
Phoenix Squad,Alice Johnson,9876543210,Bob Wilson,9123456789,Valorant
Phoenix Squad,Alice Johnson,9876543210,Charlie Brown,9111111111,Valorant
Viper's Nest,Diana Martinez,9999999999,Eve Davis,9888888888,Valorant
```

---

## Notes

- Phone numbers are exported as-is from the database (blank if not provided)
- Names use `get_full_name()` which combines first_name and last_name; falls back to username if empty
- Teams CSV creates one row per team member (so team leader appears once per member)
- If a team has no members, one row is written with empty member fields
- All scripts use UTF-8 encoding

---

## File Locations

- **Registrations Script:** `cultural/management/commands/export_registrations_csv.py`
- **Teams Script:** `cultural/management/commands/export_teams_csv.py`
