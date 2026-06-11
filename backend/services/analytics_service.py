from typing import List, Dict, Any
from datetime import datetime, date, timedelta


class AnalyticsService:
    @staticmethod
    def calculate_attendance_percentage(
        total_classes: int,
        present_classes: int
    ) -> float:
        """Calculate attendance percentage"""
        if total_classes == 0:
            return 0.0
        return round((present_classes / total_classes) * 100, 2)

    @staticmethod
    def get_student_attendance_summary(
        attendance_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate attendance summary for a student
        Returns dict with counts and percentages
        """
        total = len(attendance_records)
        present = sum(1 for r in attendance_records if r['status'] == 'present')
        absent = sum(1 for r in attendance_records if r['status'] == 'absent')
        late = sum(1 for r in attendance_records if r['status'] == 'late')
        excused = sum(1 for r in attendance_records if r['status'] == 'excused')
        
        percentage = AnalyticsService.calculate_attendance_percentage(total, present + late)
        
        return {
            'total_classes': total,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': excused,
            'percentage': percentage
        }

    @staticmethod
    def get_monthly_trend(
        attendance_records: List[Dict[str, Any]],
        months: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get monthly attendance trend data
        Returns list of monthly data points
        """
        monthly_data = {}
        
        for record in attendance_records:
            if record.get('marked_at'):
                month_key = record['marked_at'].strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'present': 0, 'total': 0}
                monthly_data[month_key]['total'] += 1
                if record['status'] in ['present', 'late']:
                    monthly_data[month_key]['present'] += 1
        
        # Sort by month and calculate percentages
        sorted_months = sorted(monthly_data.keys())[-months:]
        trend = []
        
        for month in sorted_months:
            data = monthly_data[month]
            percentage = AnalyticsService.calculate_attendance_percentage(
                data['total'], data['present']
            )
            trend.append({
                'month': month,
                'present': data['present'],
                'total': data['total'],
                'percentage': percentage
            })
        
        return trend

    @staticmethod
    def identify_defaulters(
        student_summaries: List[Dict[str, Any]],
        threshold: float = 75.0
    ) -> List[Dict[str, Any]]:
        """
        Identify students below attendance threshold
        Returns list of defaulter students
        """
        defaulters = []
        
        for summary in student_summaries:
            if summary['percentage'] < threshold:
                defaulters.append(summary)
        
        # Sort by percentage (lowest first)
        defaulters.sort(key=lambda x: x['percentage'])
        
        return defaulters

    @staticmethod
    def analyze_hourly_patterns(
        attendance_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze attendance patterns by hour
        Returns hourly statistics
        """
        hourly_data = {}
        
        for record in attendance_records:
            if record.get('marked_at'):
                hour = record['marked_at'].hour
                hour_key = f"{hour:02d}:00"
                
                if hour_key not in hourly_data:
                    hourly_data[hour_key] = {'present': 0, 'total': 0}
                
                hourly_data[hour_key]['total'] += 1
                if record['status'] in ['present', 'late']:
                    hourly_data[hour_key]['present'] += 1
        
        # Calculate percentages and find best/worst hours
        hourly_stats = []
        best_hour = None
        worst_hour = None
        best_percentage = 0
        worst_percentage = 100
        
        for hour, data in hourly_data.items():
            percentage = AnalyticsService.calculate_attendance_percentage(
                data['total'], data['present']
            )
            hourly_stats.append({
                'hour': hour,
                'present': data['present'],
                'total': data['total'],
                'percentage': percentage
            })
            
            if percentage > best_percentage:
                best_percentage = percentage
                best_hour = hour
            
            if percentage < worst_percentage:
                worst_percentage = percentage
                worst_hour = hour
        
        return {
            'hourly_data': hourly_stats,
            'best_hour': best_hour,
            'worst_hour': worst_hour
        }
