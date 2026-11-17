
import pandas as pd
import csv


# User-defined exceptions
class ItemNotFoundError(Exception):
    pass


class InvalidItemError(Exception):
    pass


class DuplicateItemError(Exception):
    pass


# Class and constructor
class ItemManager:

    def __init__(self):
        self.items = []

    # Add item
    def add_item(self, item):
        if not item["name"].strip():
            raise InvalidItemError("Item name cannot be empty")

        if item["status"] not in ["Lost", "Found"]:
            raise InvalidItemError("Invalid item status")

        self.items.append(item)

    # Search item
    def search_item(self, item_id):
        for item in self.items:
            if item["id"] == item_id:
                return item

        raise ItemNotFoundError("Item not found")

    # Delete item
    def delete_item(self, item_id):
        for item in self.items:
            if item["id"] == item_id:
                self.items.remove(item)
                return

        raise ItemNotFoundError("Item not found")

    # File handling
    def save_to_file(self, filename="items.csv"):
        try:
            with open(filename, "w", newline="", encoding="utf-8") as file:
                if self.items:
                    writer = csv.DictWriter(
                        file, fieldnames=self.items[0].keys()
                    )
                    writer.writeheader()
                    writer.writerows(self.items)

            return "Records saved successfully"

        except (OSError, csv.Error) as error:
            return f"File error: {error}"

    def read_from_file(self, filename="items.csv"):
        try:
            with open(filename, "r", encoding="utf-8") as file:
                return list(csv.DictReader(file))

        except FileNotFoundError:
            return "File does not exist"

        except (OSError, csv.Error) as error:
            return f"File error: {error}"

    # Pandas Series with labels
    def create_series(self, records):
        series = pd.Series(
            [item["name"] for item in records],
            index=[f"Item {item['id']}" for item in records],
            dtype="object"
        )

        return series
