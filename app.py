from datetime import datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
import logging
from reminder import send_reminder_email
from user_side import add_inventory, delete_inventory, edit_inventory, employee_login, get_inventory, submit_inventory_request
from admin_side import add_available_inventory, delete_inventory_items, edit_inventory_item, fetch_all_inventory_details, fetch_available_inventory_data, get_inventory_collection, modify_available_inventory
application = Flask(__name__)

# Logging setup
CORS(application)


@application.route("/")
def home():
    return jsonify({"message": "Backend is running successfully!"})
###########################################################################

# Route to fetch all available API routes
@application.route("/api/routes", methods=["GET"])
def get_routes():
    return jsonify([str(rule) for rule in application.url_map.iter_rules()])
logging.basicConfig(level=logging.DEBUG)
#############################################################################################

@application.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("email")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user_data = employee_login(username, password)  # Check credentials

    if user_data:
        if username =="admin":
            return jsonify({"user": user_data, "message": "Admin login successful"}), 200
        else:
            return jsonify({"user": user_data, "message": "Login successful"}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401
######################################################################################################
    
@application.route("/api/inventory_request", methods=["POST"])
def api_inventory_request():
    data = request.json
    employee_name = data.get("name")
    tool_needed = data.get("tool_needed")
    reason = data.get("reason")

    if not all([employee_name, tool_needed, reason]):
        return jsonify({"error": "Missing required fields"}), 400

    result = submit_inventory_request(employee_name, tool_needed, reason)
    return jsonify(result), 200
###########################################################################################################
@application.route('/api/inventory_details', methods=['GET', 'POST'])
def inventory_details():
    if request.method == 'GET':
        return get_inventory()

    data = request.get_json()

    if request.method == 'POST':
        return add_inventory(data)
    # elif request.method == 'PUT':
    #     return edit_inventory(data)
    # elif request.method == 'DELETE':
    #     return delete_inventory(data)

    logging.warning("Invalid HTTP method used on /api/inventory_details endpoint.")
    return jsonify({"success": False, "message": "Invalid request method"}), 405
    
###################################################################################################################
#This is used to get the inventory details in admin side of the employees
@application.route('/api/inventory_management', methods=['GET'])
def get_inventory_management():
    try:
        name = request.args.get("name")
        if name:
            # If name is provided, return a single employee's inventory
            collection = get_inventory_collection()
            employee = collection.find_one({"name": name}, {"_id": 0, "name": 1, "inventory_details": 1})
            if not employee:
                return jsonify({"success": False, "message": "Employee not found"}), 404
            return jsonify({"success": True, "inventory": employee}), 200
        else:
            # Otherwise, return all inventory records
            inventories = fetch_all_inventory_details()
            return jsonify({"inventories": inventories}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    
######################################################################################################################
@application.route('/api/inventory_management', methods=['POST'])
def handle_inventory_management():
    return add_available_inventory()
######################################################################################################################

@application.route('/api/inventory_available', methods=['GET'])
def get_available_inventory():
    try:
        inventory = fetch_available_inventory_data()
        return jsonify({
            "success": True,
            "inventory": inventory
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500
    
########################################################################################################################
@application.route('/api/inventory_available', methods=['POST'])
def handle_inventory_modification():
    return modify_available_inventory()
##########################################################################################################################
@application.route("/api/inventory_management", methods=["PUT", "DELETE"])
def inventory_management():
    data = request.get_json()
    name = data.get("name")

    if request.method == "PUT":
        action = data.get("action")
        original_item = data.get("original_item")
        new_item = data.get("item")
        quantity = data.get("quantity")

        if action != "edit" or not all([name, original_item, new_item, quantity is not None]):
            return jsonify({"success": False, "message": "Invalid PUT data"}), 400

        result, status_code = edit_inventory_item(name, original_item, new_item, quantity)
        return jsonify(result), status_code

    elif request.method == "DELETE":
        inventory_details = data.get("inventory_details")
        if not inventory_details or not isinstance(inventory_details, dict):
            return jsonify({"success": False, "message": "Invalid DELETE payload"}), 400

        result, status_code = delete_inventory_items(name, inventory_details)
        return jsonify(result), status_code

    return jsonify({"success": False, "message": "Unsupported HTTP method"}), 405


#####################################################################################################################################

@application.route('/api/one_on_one_meetings', methods=['GET'])
def map_managers_to_employees():
    # Connect to MongoDB
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]

    # Fetch all employee records
    employees = db.Employee_meetingdetails.find()

    # Manager to employees map
    manager_map = {}

    for emp in employees:
        manager = emp.get("manager")
        employee_name = emp.get("name")
        designation = emp.get("designation", "")  # Default to empty string if not present

        if manager:
            if manager not in manager_map:
                manager_map[manager] = []

            # Add name + designation
            manager_map[manager].append({
                "name": employee_name,
                "designation": designation
            })

    return jsonify({
        "success": True,
        "manager_employee_map": manager_map
    })


@application.route("/api/performance_meetings", methods=['GET'])
def map_managers_to_employees_for_performance():
    # Connect to MongoDB
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]

    # Fetch all employee records
    employees = db.Employee_meetingdetails.find()

    # Manager to employees map
    manager_map = {}

    for emp in employees:
        manager = emp.get("manager")
        employee_name = emp.get("name")
        designation = emp.get("designation", "")  # Default to empty string if not present

        if manager:
            if manager not in manager_map:
                manager_map[manager] = []

            # Add name + designation
            manager_map[manager].append({
                "name": employee_name,
                "designation": designation
            })

    return jsonify({
        "success": True,
        "manager_employee_map": manager_map
    })

###############################################################################################################################################
@application.route('/api/one_on_one_meetings', methods=['POST'])
def save_completed_one_on_one_meeting():
    data = request.get_json(force=True)

    required_fields = ["manager_name", "employee_name", "designation", "month", "year", "date"]
    if not all(field in data for field in required_fields):
        return jsonify({
            "success": False,
            "message": "Missing required fields"
        }), 400

    manager = data["manager_name"]
    employee = data["employee_name"]
    designation = data["designation"]
    month = data["month"]
    year = int(data["year"])
    date = data["date"]

    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]

    # First, check if document for this manager/month/year exists
    status_doc = db.One_on_one_status.find_one({
        "manager": manager,
        "month": month,
        "year": year
    })

    if status_doc:
        # Check if employee already in list
        for emp in status_doc.get("employees", []):
            if emp["name"] == employee:
                return jsonify({
                    "success": False,
                    "message": "This one-on-one meeting record already exists"
                }), 409

        # Append to existing document
        db.One_on_one_status.update_one(
            {"manager": manager, "month": month, "year": year},
            {"$push": {
                "employees": {
                    "name": employee,
                    "designation": designation,
                    "status": "completed",
                    "date": date
                }
            }}
        )
    else:
        # Create new document
        db.One_on_one_status.insert_one({
            "manager": manager,
            "month": month,
            "year": year,
            "employees": [
                {
                    "name": employee,
                    "designation": designation,
                    "status": "completed",
                    "date": date
                }
            ]
        })

    return jsonify({
        "success": True,
        "message": "One-on-one meeting saved successfully"
    }), 200



@application.route("/api/employee_status/<manager_name>/<month>/<year>")
def get_employee_meeting_status(manager_name, month, year):
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]
    # Step 1: Get all employees under this manager
    static_employees = list(db.Employee_meetingdetails.find({"manager": manager_name}))

    # Step 2: Get meeting status document for given manager/month/year
    meeting_doc = db.One_on_one_status.find_one({
        "manager": manager_name,
        "month": month,
        "year": int(year)
    })

    # Step 3: Create a lookup dictionary for employees who have completed the meeting
    completed_lookup = {}
    if meeting_doc and "employees" in meeting_doc:
        for emp in meeting_doc["employees"]:
            if emp.get("status") == "completed":
                completed_lookup[emp["name"]] = True

    # Step 4: Build final result combining static employee list + status
    result = []
    for emp in static_employees:
        emp_name = emp.get("name")
        emp_status = "completed" if emp_name in completed_lookup else "pending"
        result.append({
            "name": emp_name,
            "designation": emp.get("designation", ""),
            "manager": emp.get("manager", ""),
            "status": emp_status
        })

    return jsonify({
        "success": True,
        "manager": manager_name,
        "month": month,
        "year": year,
        "employees": result
    })

@application.route("/api/performance_status/<manager_name>/<month>/<year>")
def get_performance_status(manager_name, month, year):
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]

    # Static data: get all employees under this manager
    static_employees = list(db.Employee_meetingdetails.find({"manager": manager_name}))

    # Performance tracking data
    performance_doc = db.Performance_status.find_one({
        "manager": manager_name,
        "month": month,
        "year": int(year)
    })

    # Lookup for completed employees
    completed_lookup = {}
    if performance_doc and "employees" in performance_doc:
        for emp in performance_doc["employees"]:
            if emp.get("status") == "completed":
                completed_lookup[emp["name"]] = True

    # Build the response
    employee_list = []
    for emp in static_employees:
        emp_name = emp.get("name")
        employee_list.append({
            "name": emp_name,
            "designation": emp.get("designation", ""),
            "status": "completed" if emp_name in completed_lookup else "pending"
        })

    return jsonify({
        "success": True,
        "manager": manager_name,
        "month": month,
        "year": year,
        "employees": employee_list
    })




@application.route("/api/performance_meetings", methods=['POST'])
def save_completed_performance_meeting():
    data = request.get_json(force=True)

    required_fields = ["manager_name", "employee_name", "designation", "month", "year", "date"]
    if not all(field in data for field in required_fields):
        return jsonify({
            "success": False,
            "message": "Missing required fields"
        }), 400

    manager = data["manager_name"]
    employee = data["employee_name"]
    designation = data["designation"]
    month = data["month"]
    year = int(data["year"])
    date = data["date"]

    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]

    # First, check if document for this manager/month/year exists
    status_doc = db.Performance_status.find_one({
        "manager": manager,
        "month": month,
        "year": year
    })

    if status_doc:
        # Check if employee already in list
        for emp in status_doc.get("employees", []):
            if emp["name"] == employee:
                return jsonify({
                    "success": False,
                    "message": "This one-on-one meeting record already exists"
                }), 409

        # Append to existing document
        db.Performance_status.update_one(
            {"manager": manager, "month": month, "year": year},
            {"$push": {
                "employees": {
                    "name": employee,
                    "designation": designation,
                    "status": "completed",
                    "date": date
                }
            }}
        )
    else:
        # Create new document
        db.Performance_status.insert_one({
            "manager": manager,
            "month": month,
            "year": year,
            "employees": [
                {
                    "name": employee,
                    "designation": designation,
                    "status": "completed",
                    "date": date
                }
            ]
        })

    return jsonify({
        "success": True,
        "message": "One-on-one meeting saved successfully"
    }), 200



# @application.route("/api/one_on_one_meetings", methods=["GET"])
# def map_managers_to_employees():
#     data = get_one_on_one_mapping()
#     return jsonify({
#         "success": True,
#         "manager_employee_map": data
#     })


# @application.route("/api/performance_meetings", methods=["GET"])
# def map_managers_to_employees_for_performance():
#     data = get_one_on_one_mapping()  # same function reused
#     return jsonify({
#         "success": True,
#         "manager_employee_map": data
#     })


# @application.route("/api/one_on_one_meetings", methods=["POST"])
# def save_completed_one_on_one_meeting():
#     data = request.get_json(force=True)
#     required_fields = ["manager_name", "employee_name", "designation", "month", "year", "date"]

#     if not all(field in data for field in required_fields):
#         return jsonify({
#             "success": False,
#             "message": "Missing required fields"
#         }), 400

#     success, msg = save_meeting(data)
#     if not success:
#         return jsonify({
#             "success": False,
#             "message": msg
#         }), 409

#     return jsonify({
#         "success": True,
#         "message": msg
#     })


# @application.route("/api/employee_status/<manager_name>/<month>/<year>")
# def get_employee_meeting_status(manager_name, month, year):
#     data = get_meeting_status(manager_name, month, year)
#     data["success"] = True
#     return jsonify(data)

####################################################################################################################
@application.route("/api/monthly-oneonone-reminder", methods=["POST"])
def send_monthly_oneonone_reminder():
    # MongoDB setup
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]

    # Current month and year
    now = datetime.now()
    month = now.strftime("%B")  # Example: "June"
    year = now.year

    # Step 1: Get distinct manager names from employee data
    managers = db.Employee_meetingdetails.distinct("manager")

    # Step 2: For each manager, get their email and send reminder
    for manager in managers:
        employee = db.Employee_meetingdetails.find_one({"manager": manager})
        if employee and "manager_email" in employee:
            manager_email = employee["manager_email"]

            # Email content
            subject = "Monthly One-on-One Reminder"
            body = f"""
Dear {manager},

This is a reminder to complete your One-on-One meetings for the month of {month} {year}.

Please log all completed meetings in the system.

Thank you,
HR Automation Team
            """

            # Send the email
            send_reminder_email(to_email=manager_email, subject=subject, body=body)

    return jsonify({
        "success": True,
        "message": "One-on-One email reminders sent successfully"
    })


@application.route("/api/monthly-performance-reminder", methods=["POST"])
def send_monthly_performance_reminder():
    # MongoDB connection
    client = MongoClient("mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/")
    db = client["Timesheet"]

    # Get current month and year
    now = datetime.now()
    month = now.strftime("%B")  # e.g., "June"
    year = now.year

    # Get distinct manager names from employee data
    managers = db.Employee_meetingdetails.distinct("manager")

    for manager in managers:
        employee = db.Employee_meetingdetails.find_one({"manager": manager})
        if employee and "manager_email" in employee:
            manager_email = employee["manager_email"]

            # Email content
            subject = f"Performance Review Reminder – {month} {year}"
            body = f"""
Dear {manager},

This is a reminder to complete performance reviews for your team for the month of {month} {year}.

Please make sure to update the performance meeting status in the system.

Login here: https://singh-automation-hr-management.netlify.app/login/  
Username: admin  
Password: admin

Thank you,  
HR Automation Team
            """

            # Send the email
            send_reminder_email(to_email=manager_email, subject=subject, body=body)

    return jsonify({
        "success": True,
        "message": "Performance email reminders sent successfully"
    })