from django.core.management.base import BaseCommand
import pandas as pd
from api.models import FuelStop


class Command(BaseCommand):
    help = "Load fuel stops from a CSV file into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file", type=str, help="Path to the CSV file containing fuel stop data"
        )

    def handle(self, *args, **kwargs):
        csv_file = kwargs["csv_file"]
        data = pd.read_csv(csv_file)
        for _, row in data.iterrows():
            FuelStop.objects.create(
                opis_truckstop_id=row["OPIS Truckstop ID"],
                truckstop_name=row["Truckstop Name"],
                address=row["Address"],
                city=row["City"],
                state=row["State"],
                rack_id=(
                    row["Rack ID"] if pd.notna(row["Rack ID"]) else None
                ),  # Handle missing Rack ID
                retail_price=row["Retail Price"],
            )
        self.stdout.write(self.style.SUCCESS("Successfully loaded fuel data from CSV"))
