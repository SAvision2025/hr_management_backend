from pymongo import MongoClient
from flask import jsonify, request
from pymongo import MongoClient

def get_inventory_collection():
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]
    return db["Employee_Inventory_details"]

def fetch_all_inventory_details():
    """
    Fetch and format inventory data from the Employee_Inventory_details collection.
    Returns:
        List[Dict]: A list of formatted inventory dictionaries.
    """
    collection = get_inventory_collection()
    raw_data = list(collection.find({}, {"_id": 0}))  # Exclude MongoDB _id

    formatted_data = [
        {"inventory": employee}
        for employee in raw_data
    ]
    return formatted_data

def add_available_inventory():
    """
    Adds or increments an item in the Available_inventory collection.
    Expects JSON with 'action', 'item', and 'quantity'.
    """
    try:
        data = request.get_json()
        action = data.get("action")
        item = data.get("item")
        quantity = data.get("quantity")

        if not all([action, item, quantity]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        if action != "add":
            return jsonify({"success": False, "message": "Unsupported action"}), 400

        # MongoDB connection and collection
        client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
        db = client["Timesheet"]
        collection = db["Available_Inventory"]

        # Increment or add the item
        collection.update_one(
            {},  # Using a single document to track all inventory items
            {"$inc": {item: quantity}},
            upsert=True
        )

        return jsonify({"success": True, "message": f"{item} added with quantity {quantity}"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


def fetch_available_inventory_data():
    """
    Connects to MongoDB and retrieves all available inventory items from the Available_Inventory collection.
    Returns:
        Dict: A dictionary mapping item names to their quantities.
    """
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]
    collection = db["Available_Inventory"]

    inventory_data = collection.find({})
    inventory_dict = {}

    for item in inventory_data:
        for key, value in item.items():
            if key != "_id":
                inventory_dict[key] = value

    return inventory_dict

def modify_available_inventory():
    try:
        data = request.get_json()
        action = data.get("action")
        asset = data.get("asset")
        quantity = data.get("quantity")

        if not all([action, asset, quantity]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
        db = client["Timesheet"]
        collection = db["Available_Inventory"]

        if action == "edit":
            result = collection.update_one(
                {},
                {"$set": {asset: quantity}}
            )
            return jsonify({"success": True, "message": f"{asset} quantity updated to {quantity}"}), 200

        elif action == "delete":
            existing_doc = collection.find_one({}, {"_id": 0})
            if not existing_doc or asset not in existing_doc:
                return jsonify({"success": False, "message": f"{asset} not found"}), 404

            current_quantity = existing_doc[asset]
            new_quantity = current_quantity - quantity

            if new_quantity <= 0:
                # Only remove the specific field (not entire document)
                collection.update_one(
                    {},
                    {"$unset": {asset: ""}}
                )
                return jsonify({"success": True, "message": f"{asset} completely removed"}), 200
            else:
                collection.update_one(
                    {},
                    {"$set": {asset: new_quantity}}
                )
                return jsonify({"success": True, "message": f"{asset} quantity reduced to {new_quantity}"}), 200

        else:
            return jsonify({"success": False, "message": "Invalid action"}), 400

    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    

####################################################################################################################################
def edit_inventory_item(name, original_item, new_item, quantity):
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]
    collection = db["Employee_Inventory_details"]

    employee = collection.find_one({"name": name})

    if not employee or "inventory_details" not in employee:
        return {"success": False, "message": "Employee or inventory not found"}, 404

    if original_item not in employee["inventory_details"]:
        return {"success": False, "message": "Original item not found"}, 404

    # Unset the original item and set the new one
    collection.update_one({"name": name}, {"$unset": {f"inventory_details.{original_item}": ""}})
    collection.update_one({"name": name}, {"$set": {f"inventory_details.{new_item}": quantity}})

    return {"success": True, "message": f"Item renamed to '{new_item}' with quantity {quantity}"}, 200


def delete_inventory_items(name, inventory_details):
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]
    collection = db["Employee_Inventory_details"]

    # Construct unset query
    unset_query = {f"inventory_details.{item}": "" for item in inventory_details}

    result = collection.update_one({"name": name}, {"$unset": unset_query})

    if result.modified_count == 0:
        return {"success": False, "message": "Nothing deleted or item(s) not found"}, 404

    return {"success": True, "message": "Item(s) deleted successfully"}, 200


