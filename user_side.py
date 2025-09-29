import logging
from flask import jsonify, request
from pymongo import MongoClient
from mail import send_inventory_email_to_manager


def employee_login(emp_name, emp_password):
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]
    collection = db["Employee_credentials"]
    user = collection.find_one({"Username": emp_name})
    if not user:
        return None

    username = user["Username"]
    password = user["Password"]
    if username == emp_name and password == emp_password:
        if username == "admin":
            return {"Username": username, "message": "Admin login successful"}
        else:
            return {"Username": username, "message": "Login successful"}
    else:
        return None


def get_manager_details(emp_name):
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]
    collection = db["Employee_data"]
    data = collection.find_one({"name": emp_name})
    if data:
        return data.get("manager"), data.get("manager_email")
    else:
        print(f"No manager found for employee: {emp_name}")
        return None, None

from bson import ObjectId

def submit_inventory_request(employee_name, tool_needed, reason):
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]
    collection = db["Inventory_requests"]

    request_data = {
        "employee_name": employee_name,
        "tool_needed": tool_needed,
        "reason": reason
    }

    # Insert and get the ObjectId
    inserted_id = collection.insert_one(request_data).inserted_id
    request_data["_id"] = str(inserted_id)  # Convert ObjectId to string for JSON

    # Email manager
    manager_name, manager_email = get_manager_details(employee_name)
    if manager_name and manager_email:
        send_inventory_email_to_manager(
            employee_name,
            tool_needed,
            reason,
            manager_name,
            manager_email
        )

    return {
        "message": "Inventory request submitted successfully",
        "request": request_data
    }



def get_inventory_collection(collection_name):
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]
    return db[collection_name]


def get_inventory():
    name = request.args.get("name")
    if not name:
        logging.error("Employee name is required to fetch inventory.")
        return jsonify({"success": False, "message": "Employee name is required"}), 400

    logging.info(f"Fetching inventory for employee: {name}")
    collection = get_inventory_collection("Employee_Inventory_details")
    employee_data = collection.find_one({"name": name}, {"_id": 0})

    if not employee_data:
        logging.warning(f"No inventory found for employee: {name}")
        return jsonify({"success": False, "message": "No inventory found for this employee"}), 404

    return jsonify({"success": True, "inventory": employee_data})


def add_inventory(data):
    name = data.get("name")
    item = data.get("item")
    quantity = data.get("quantity")
    logging.info(f"Assigning '{item}' (qty: {quantity}) to employee '{name}'.")

    collection = get_inventory_collection("Employee_Inventory_details")
    existing = collection.find_one({"name": name})

    if existing:
        collection.update_one(
            {"name": name},
            {"$set": {f"inventory_details.{item}": quantity}}
        )
    else:
        collection.insert_one({
            "name": name,
            "inventory_details": {
                item: quantity
            }
        })

    logging.info(f"Item '{item}' successfully assigned to {name}.")
    return jsonify({"success": True, "asset": {"name": name, item: quantity}})


def edit_inventory(data):
    name = data.get("name")
    item = data.get("item")
    quantity = data.get("quantity")
    logging.info(f"Updating item '{item}' for employee '{name}' to quantity {quantity}.")

    collection = get_inventory_collection("Employee_Inventory_details")
    result = collection.update_one(
        {"name": name, f"inventory_details.{item}": {"$exists": True}},
        {"$set": {f"inventory_details.{item}": quantity}}
    )

    if result.matched_count == 0:
        logging.error(f"Item '{item}' not found for employee '{name}'.")
        return jsonify({"success": False, "message": "Item not found"}), 404

    logging.info(f"Item '{item}' updated successfully for {name}.")
    return jsonify({"success": True, "message": "Asset updated"})


def delete_inventory(data):
    employee_name = data.get("name")
    inventory_details = data.get("inventory_details")

    if not employee_name or not inventory_details:
        logging.error("Missing 'name' or 'inventory_details' in request data.")
        return jsonify({"success": False, "message": "Invalid request data"}), 400

    item_name = next(iter(inventory_details))  # Get the first key from inventory_details

    collection = get_inventory_collection("Employee_Inventory_details")

    result = collection.update_one(
        {"name": employee_name},
        {"$unset": {f"inventory_details.{item_name}": ""}}
    )

    if result.modified_count == 0:
        logging.warning("No matching record found to delete item '%s' for employee '%s'.", item_name, employee_name)
        return jsonify({"success": False, "message": "Item not found for employee"}), 404

    logging.info("Item '%s' removed from inventory assigned to employee '%s'.", item_name, employee_name)
    return jsonify({"success": True, "message": f"Item '{item_name}' removed for employee '{employee_name}'"})
