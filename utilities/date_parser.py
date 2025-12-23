"""Date parsing utilities for Audio Transcriber."""
import os
import re
from datetime import datetime


class DateParser:
    """Utilities for parsing dates from filenames."""
    
    @staticmethod
    def detect_date_from_filename(filename):
        """Detect date from filename.
        
        Args:
            filename: Filename to parse.
            
        Returns:
            Tuple of (detected_date, day_of_week) or (None, None).
        """
        name_without_ext = os.path.splitext(filename)[0]
        
        patterns = [
            (r'(\d{4})[-_.](\d{2})[-_.](\d{2})', '%Y-%m-%d'),
            (r'(\d{4})(\d{2})(\d{2})', '%Y%m%d'),
            (r'(\d{2})[-_.](\d{2})[-_.](\d{4})', '%m-%d-%Y'),
            (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-_.\s]+(\d{1,2})[-_.\s]+(\d{4})', 'month_name'),
        ]
        
        for pattern, date_format in patterns:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                try:
                    if date_format == 'month_name':
                        month_str = match.group(1)
                        day = int(match.group(2))
                        year = int(match.group(3))
                        date_str = f"{month_str} {day} {year}"
                        detected_date = datetime.strptime(date_str, '%b %d %Y')
                    else:
                        date_str = '-'.join(match.groups())
                        detected_date = datetime.strptime(date_str, date_format)
                    
                    day_of_week = detected_date.strftime('%A')
                    return detected_date, day_of_week
                except ValueError:
                    continue
        
        return None, None
