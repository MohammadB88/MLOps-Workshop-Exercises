import json
import os
from datetime import datetime


class AuditLogger:
    """Simple audit logger for ML system events.

    Stores events as newline-delimited JSON (JSONL) for append-only,
    human-readable audit trails without external database dependencies.
    """

    def __init__(self, log_file='audit_log.jsonl'):
        self.log_file = log_file
        if not os.path.exists(log_file):
            with open(log_file, 'w'):
                pass

    def log_event(self, event_type, user, resource, details=None):
        """Log an auditable event.

        Args:
            event_type: Category of event (e.g., 'prediction', 'model_registration').
            user: Identity performing the action.
            resource: The object the action was performed on.
            details: Optional dict with additional context.

        Returns:
            The event dict that was logged.
        """
        event = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event_type': event_type,
            'user': user,
            'resource': resource,
            'details': details or {}
        }
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
        return event

    def query_events(self, filters=None):
        """Query events with optional filters.

        Args:
            filters: Dict of key-value pairs to filter by. Only events
                     matching all filter criteria are returned.

        Returns:
            List of matching event dicts.
        """
        filters = filters or {}
        results = []
        if not os.path.exists(self.log_file):
            return results
        with open(self.log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                match = True
                for key, value in filters.items():
                    if key in event and event[key] != value:
                        match = False
                        break
                if match:
                    results.append(event)
        return results

    def export_report(self, format='json'):
        """Export all events as a formatted report.

        Args:
            format: Output format ('json' or 'csv').

        Returns:
            Formatted string of all audit events.
        """
        events = self.query_events()
        if format == 'json':
            return json.dumps(events, indent=2)
        elif format == 'csv':
            import csv
            import io
            output = io.StringIO()
            if events:
                writer = csv.DictWriter(output, fieldnames=events[0].keys())
                writer.writeheader()
                writer.writerows(events)
            return output.getvalue()
        else:
            return str(events)

    def clear(self):
        """Clear all events from the log file (use with caution)."""
        with open(self.log_file, 'w'):
            pass
