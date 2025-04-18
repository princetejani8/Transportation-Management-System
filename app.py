import streamlit as st
import mysql.connector
import pandas as pd
from datetime import date

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import base64

# Database connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Prince@123",
    database="tms"
)
cursor = conn.cursor()

# Utility functions to get dropdown options
def get_staff_options():
    cursor.execute("SELECT staff_id, full_name FROM staff")
    return cursor.fetchall()

def get_vehicle_options():
    cursor.execute("SELECT vehicle_id, vehicle_type FROM vehicle")  # Fetch only vehicle_id and vehicle_type
    options = cursor.fetchall()
    return options


# Add Staff
def add_staff():
    st.subheader("➕ Add Staff")
    with st.form("staff_form"):
        full_name = st.text_input("Full Name")
        role = st.text_input("Role")
        phone = st.text_input("Phone Number")
        email = st.text_input("Email")
        address = st.text_area("Address")
        submitted = st.form_submit_button("Add Staff")

        if submitted:
            cursor.execute("INSERT INTO staff (full_name, role, phone_number, email, address) VALUES (%s, %s, %s, %s, %s)",
                           (full_name, role, phone, email, address))
            conn.commit()
            st.success("✅ Staff added successfully!")

# Add Vehicle
def add_vehicle():
    st.subheader("🚗 Add Vehicle")
    
    with st.form("vehicle_form"):
        # Vehicle Number Plate input
        vehicle_number_plate = st.text_input("Enter Vehicle Number Plate", value=st.session_state.get('vehicle_number_plate', ""))
        
        # Vehicle type, capacity (in kg), and driver's name
        vehicle_type = st.selectbox("Select Vehicle Type", ["Truck", "Van", "Car", "Bus", "Bike"])
        vehicle_capacity_kg = st.number_input("Capacity (in kg)", min_value=0.0, value=st.session_state.get('vehicle_capacity_kg', 0.0))
        driver_name = st.text_input("Enter Driver's Name")
        
        # Submit button
        submitted = st.form_submit_button("Add Vehicle")
        
        if submitted:
            if vehicle_number_plate and vehicle_type and vehicle_capacity_kg > 0 and driver_name:
                try:
                    # Insert vehicle data into the MySQL database, excluding vehicle_number
                    cursor.execute("""
                        INSERT INTO vehicle (vehicle_type, capacity_kg, number_plate, driver_name)
                        VALUES (%s, %s, %s, %s)
                    """, (vehicle_type, vehicle_capacity_kg, vehicle_number_plate, driver_name))
                    conn.commit()
                    
                    st.success("✅ Vehicle added successfully!")
                    
                    # Reset the form fields after submission
                    st.session_state.vehicle_number_plate = ""
                    st.session_state.vehicle_capacity_kg = 0.0
                    st.session_state.driver_name = ""
                except Exception as e:
                    st.error(f"❌ Error adding vehicle: {e}")
            else:
                st.error("❌ Please fill in all required fields with valid data!")

# Generate Bill
def generate_bill():
    st.subheader("🧾 Generate Bill")
    
    with st.form("bill_form"):
        # Select vehicle and staff
        vehicle = st.selectbox(
            "Select Vehicle", 
            get_vehicle_options(), 
            format_func=lambda x: f"{x[1]}"  # Only show vehicle_type here
        )
        staff = st.selectbox("Select Staff", get_staff_options(), format_func=lambda x: f"{x[1]}")
        
        # Input for billing details
        weight = st.number_input("Weight (kg)", min_value=0.0, value=st.session_state.get('weight', 0.0))
        price_per_kg = st.number_input("Price per kg (₹)", min_value=0.0, value=st.session_state.get('price_per_kg', 0.0))
        description = st.text_area("Description (optional)", value=st.session_state.get('description', ""))
        
        # Calculate total amount
        if weight > 0 and price_per_kg > 0:
            total = weight * price_per_kg
            st.markdown(f"### 💰 Total Amount: ₹ {total:.2f}")
        else:
            total = 0.0
            st.markdown("### 💰 Total Amount: ₹ 0.00")
        
        # Submit button
        submitted = st.form_submit_button("Generate Bill")
        
        if submitted:
            if vehicle and staff and weight > 0 and price_per_kg > 0:
                try:
                    # Insert bill data into MySQL database (EXCLUDE total_amount column)
                    cursor.execute("""
                        INSERT INTO bill (vehicle_id, staff_id, billing_date, weight_kg, price_per_kg, description)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (vehicle[0], staff[0], date.today(), weight, price_per_kg, description))
                    conn.commit()
                    
                    # Fetch generated bill details
                    cursor.execute("SELECT LAST_INSERT_ID()")
                    bill_id = cursor.fetchone()[0]
                    cursor.execute("""
                        SELECT bill_id, s.full_name AS staff_name, v.vehicle_number, bill.billing_date,
                               bill.weight_kg, bill.price_per_kg, bill.total_amount, bill.description
                        FROM bill
                        JOIN staff s ON bill.staff_id = s.staff_id
                        JOIN vehicle v ON bill.vehicle_id = v.vehicle_id
                        WHERE bill.bill_id = %s
                    """, (bill_id,))
                    bill_data = cursor.fetchone()
                    
                    bill_data_dict = {
                        "bill_id": bill_data[0],
                        "billing_date": bill_data[3],
                        "staff_name": bill_data[1],
                        "vehicle_number": bill_data[2],
                        "weight_kg": bill_data[4],
                        "price_per_kg": bill_data[5],
                        "total_amount": bill_data[6],
                        "description": bill_data[7]
                    }
                    
                    st.success("✅ Bill generated successfully!")
                    
                    # PDF generation and download
                    pdf_stream = generate_pdf(bill_data_dict)
                    pdf_base64 = pdf_to_base64(pdf_stream)
                    pdf_link = f'<a href="data:application/pdf;base64,{pdf_base64}" download="bill_{bill_id}.pdf">Download Bill PDF</a>'
                    st.markdown(pdf_link, unsafe_allow_html=True)
                    
                    # Reset the form fields immediately after generating the bill
                    st.session_state.weight = 0.0
                    st.session_state.price_per_kg = 0.0
                    st.session_state.description = ""
                    
                except Exception as e:
                    st.error(f"❌ Error generating bill: {e}")
            else:
                st.error("❌ Please fill in all required fields with valid data!")




# Show Staff
def show_staff():
    st.subheader("👥 Staff Records")
    cursor.execute("SELECT * FROM staff")
    data = cursor.fetchall()
    df = pd.DataFrame(data, columns=[i[0] for i in cursor.description])
    st.dataframe(df, use_container_width=True)

# Show Vehicles
def show_vehicles():
    st.subheader("🚚 Vehicle Records")
    cursor.execute("SELECT * FROM vehicle")
    data = cursor.fetchall()
    df = pd.DataFrame(data, columns=[i[0] for i in cursor.description])
    st.dataframe(df, use_container_width=True)

# Show Bills
def show_bills():
    st.subheader("🧾 Bill Records")
    cursor.execute("""
        SELECT bill.bill_id, s.full_name, v.vehicle_number, billing_date, weight_kg, price_per_kg, total_amount, description
        FROM bill
        JOIN staff s ON bill.staff_id = s.staff_id
        JOIN vehicle v ON bill.vehicle_id = v.vehicle_id
        ORDER BY billing_date DESC
    """)
    data = cursor.fetchall()
    df = pd.DataFrame(data, columns=[i[0] for i in cursor.description])
    st.dataframe(df, use_container_width=True)

# Helper: Generate PDF from bill data
def generate_pdf(bill_data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 50, "TRANSPORTATION BILL")

    c.setFont("Helvetica", 12)
    y = height - 100
    spacing = 20

    for key, value in bill_data.items():
        label = key.replace("_", " ").capitalize()
        c.drawString(50, y, f"{label}:")
        c.drawString(200, y, str(value))
        y -= spacing

    c.save()
    buffer.seek(0)
    return buffer

# Helper: Convert PDF to base64 for download link
def pdf_to_base64(pdf_buffer):
    pdf_bytes = pdf_buffer.getvalue()
    b64 = base64.b64encode(pdf_bytes).decode()
    return b64


# Sidebar Navigation
st.sidebar.title("🚦 TMS Beast Edition")
menu = st.sidebar.selectbox("Choose Action", [
    "Add Staff", "Add Vehicle", "Generate Bill",
    "Show Staff", "Show Vehicles", "Show Bills"
])

if menu == "Add Staff":
    add_staff()
elif menu == "Add Vehicle":
    add_vehicle()
elif menu == "Generate Bill":
    generate_bill()
elif menu == "Show Staff":
    show_staff()
elif menu == "Show Vehicles":
    show_vehicles()
elif menu == "Show Bills":
    show_bills()
