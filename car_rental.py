"""Car rental demo with safer input handling and file operations."""
import hashlib
import re
import secrets
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

# Global rental state for the lab demo.
fleet = {}
bookings = []
conn = sqlite3.connect(":memory:")
conn.execute(
    "CREATE TABLE customers (name TEXT, licence TEXT, phone TEXT)"
)


def addCar(plate, model="Unknown", daily_rate=0, features=None):
    """Add a car to the fleet after validating its basic data."""
    if not isValidPlate(plate):
        raise ValueError("Invalid number plate")
    if not isinstance(daily_rate, (int, float)) or daily_rate < 0:
        raise ValueError("Daily rate must be a non-negative number")
    if features is None:
        features = []
    fleet[plate] = {
        "model": model,
        "rate": daily_rate,
        "available": True,
        "features": list(features),
    }
    return fleet[plate]


def registerCustomer(name, licence, phone):
    """Register a customer using parameterized SQL."""
    conn.execute(
        "INSERT INTO customers (name, licence, phone) VALUES (?, ?, ?)",
        (name, licence, phone),
    )


def findCustomer(name):
    """Find customers by exact name without SQL string interpolation."""
    return conn.execute(
        "SELECT * FROM customers WHERE name = ?", (name,)
    ).fetchall()


def rentCar(plate, customer, start, end):
    """Create a booking and reject invalid dates or unavailable cars."""
    if not findCustomer(customer):
        raise ValueError("Customer not registered")
    if plate not in fleet:
        raise ValueError("Unknown car")
    if not fleet[plate]["available"]:
        raise ValueError("Car is not available")
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    days = (end_date - start_date).days
    if days <= 0:
        raise ValueError("End date must be after start date")
    cost = days * fleet[plate]["rate"]
    booking = {
        "code": bookingCode(),
        "plate": plate,
        "customer": customer,
        "days": days,
        "cost": cost,
    }
    bookings.append(booking)
    fleet[plate]["available"] = False
    return cost


def returnCar(plate, km_driven):
    """Mark a known car available and calculate any extra-km charge."""
    if plate not in fleet:
        raise ValueError("Unknown car")
    if not isinstance(km_driven, (int, float)) or km_driven < 0:
        raise ValueError("Kilometres driven must be non-negative")
    fleet[plate]["available"] = True
    if km_driven > 300:
        return (km_driven - 300) * 5
    return 0


def bookingCode():
    """Create a hard-to-guess booking code."""
    return f"BK-{secrets.randbelow(90000) + 10000}"


def licenceHash(licence):
    """Return a SHA-256 digest of a licence identifier."""
    return hashlib.sha256(licence.encode("utf-8")).hexdigest()


def applyPromo(rule, amount):
    """Apply only a simple discount multiplier; never execute input as code."""
    match = re.fullmatch(
        r"\s*amount\s*=\s*amount\s*\*\s*(0(?:\.\d+)?|1(?:\.0+)?)\s*",
        rule,
    )
    if not match:
        raise ValueError("Unsupported promo rule")
    factor = float(match.group(1))
    if not 0 <= factor <= 1:
        raise ValueError("Promo multiplier must be between 0 and 1")
    if amount < 0:
        raise ValueError("Amount must be non-negative")
    return amount * factor


def isValidPlate(plate):
    """Check the expected Indian-style registration format."""
    return bool(re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}", plate))


def writeReceipt(booking):
    """Write a receipt to a uniquely named file with restricted permissions."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        prefix="car_rental_receipt_",
        delete=False,
    ) as receipt:
        receipt.write(
            f"Booking {booking['code']}: {booking['plate']} for "
            f"{booking['days']} days = Rs.{booking['cost']}\n"
        )
        path = Path(receipt.name)
    try:
        path.chmod(0o600)
    except OSError:
        # Some platforms do not support POSIX file permissions.
        pass
    return str(path)


def adminLogin(user, password="admin@rent"):
    """Demo-only admin check; production credentials must be external."""
    return user == "admin" and password == "admin@rent"


def availableCars():
    """Return all currently available registration plates."""
    return [plate for plate, car in fleet.items() if car["available"]]


def main():
    addCar("KA01AB1234", "Swift", 1500)
    addCar("KA02CD5678", "Innova", 3000)
    addCar("KA03EF9999", "Nexon", 0)
    registerCustomer("Ravi", "DL-0420110012345", "9845012345")
    registerCustomer("Meera", "DL-0420110099999", "9845099999")
    print("Rent Swift:", rentCar("KA01AB1234", "Ravi", "2026-11-01", "2026-11-04"))
    print("Return charge:", returnCar("KA01AB1234", 420))
    print("Lookup injection payload:", findCustomer("x' OR '1'='1"))
    print("Promo price:", applyPromo("amount = amount * 0.9", 4500))
    print("Plate valid?", isValidPlate("KA01AB1234"))
    print("Licence hash:", licenceHash("DL-0420110012345"))
    print("Admin:", adminLogin("admin"))
    print("Available:", availableCars())
    print("Receipt saved to:", writeReceipt(bookings[0]))


if __name__ == "__main__":
    main()
