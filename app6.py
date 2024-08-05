import streamlit as st
import sqlite3
from PIL import Image
import io
import base64
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
from streamlit_extras import app_logo
from streamlit_extras.app_logo import add_logo
import datetime

# Set page config for consistent styling
st.set_page_config(page_title="My App", layout="wide")

# Custom CSS for styling
st.markdown("""
    <style>
    .reportview-container {
        margin-top: -2em;
    }
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    #stDecoration {display:none;}
    
    .stApp {
        background-image: linear-gradient(135deg, rgba(128, 0, 128, 0.3), transparent);
        backdrop-filter: blur(10px);
        color: white;
    }
    .stButton>button {
        background-color: #1E88E5;
        color: white;
        transition: transform 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.05);
    }
    .stTextInput>div>div>input {
        background-color: #2C2C2C;
        color: white;
    }
    .full-width-image {
        width: 100vw;
        height: 100vh;
        object-fit: cover;
        position: absolute;
        top: 0;
        left: 0;
        z-index: -1;
    }
    .centered-buttons {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
    }
    .centered-buttons button {
        margin: 0 10px;
    }
    .centered-title {
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# Create a connection to the SQLite database
@st.cache_resource
def get_database_connection():
    conn = sqlite3.connect("mydatabase.db", check_same_thread=False)
    return conn

conn = get_database_connection()
cursor = conn.cursor()

# Create tables (if they don't exist)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        email TEXT,
        restore_phrase TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        is_popular INTEGER,
        description TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        date DATE,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS hosts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
""")

conn.commit()

# Add example purchases
cursor.execute("SELECT COUNT(*) FROM purchases")
if cursor.fetchone()[0] == 0:
    example_purchases = [
        (1, 1, 2, '2024-08-01'),
        (2, 2, 1, '2024-08-02'),
        (3, 3, 3, '2024-08-03')
    ]
    cursor.executemany("INSERT INTO purchases (user_id, product_id, quantity, date) VALUES (?, ?, ?, ?)", example_purchases)
    conn.commit()

# Global variables
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'current_host' not in st.session_state:
    st.session_state.current_host = None
if 'page' not in st.session_state:
    st.session_state.page = "Login"

# Define functions for user authentication
def signup(username, password, email, restore_phrase):
    try:
        cursor.execute("INSERT INTO users (username, password, email, restore_phrase) VALUES (?,?,?,?)", (username, password, email, restore_phrase))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE username =?", (username,))
        user = cursor.fetchone()
        st.session_state.current_user = user
        st.success("Account created successfully!")
        return True
    except sqlite3.IntegrityError:
        st.error("Username already exists")
        return False

def login(username, password):
    cursor.execute("SELECT * FROM users WHERE username =? AND password =?", (username, password))
    user = cursor.fetchone()
    if user:
        st.session_state.current_user = user
        st.session_state.page = "User Home"
        return True
    else:
        cursor.execute("SELECT * FROM hosts WHERE username =? AND password =?", (username, password))
        host = cursor.fetchone()
        if host:
            st.session_state.current_host = host
            st.session_state.page = "Host Dashboard"
            return True
        else:
            st.error("Invalid username or password")
            return False

def change_password(new_password):
    cursor.execute("UPDATE users SET password =? WHERE id =?", (new_password, st.session_state.current_user[0]))
    conn.commit()
    st.success("Password changed successfully!")

def change_host_password(new_password):
    cursor.execute("UPDATE hosts SET password =? WHERE id =?", (new_password, st.session_state.current_host[0]))
    conn.commit()
    st.success("Password changed successfully!")

# Define page layouts
def signup_page():
    st.markdown('<h1 class="centered-title">Sign Up</h1>', unsafe_allow_html=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    email = st.text_input("Email")
    restore_phrase = st.text_input("Restore Phrase")
    if st.button("Sign Up"):
        if signup(username, password, email, restore_phrase):
            st.session_state.page = "User Home"
            st.rerun()

def login_page():
    st.markdown('<h1 class="centered-title">Login</h1>', unsafe_allow_html=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Log In"):
        if login(username, password):
            st.rerun()
    if st.button("Sign Up"):
        st.session_state.page = "Sign Up"
        st.rerun()
    if st.button("Forgot Password"):
        st.session_state.page = "Forgot Password"
        st.rerun()

def forgot_password_page():
    st.markdown('<h1 class="centered-title">Forgot Password</h1>', unsafe_allow_html=True)
    username = st.text_input("Username")
    restore_phrase = st.text_input("Restore Phrase")
    new_password = st.text_input("New Password", type="password")
    if st.button("Reset Password"):
        cursor.execute("SELECT * FROM users WHERE username =? AND restore_phrase =?", (username, restore_phrase))
        user = cursor.fetchone()
        if user:
            cursor.execute("UPDATE users SET password =? WHERE id =?", (new_password, user[0]))
            conn.commit()
            st.success("Password reset successfully!")
            st.session_state.page = "Login"
            st.rerun()
        else:
            st.error("Invalid username or restore phrase")

def create_product_card(product):
    col1, col2 = st.columns([1, 3])
    with col1:
        # Image placeholder
        img = Image.new('RGB', (100, 100), color='gray')
        st.image(img, use_column_width=True)
    with col2:
        st.subheader(product[1])
        st.write(f"${product[2]:.2f}")
        st.write(product[4])  # Description
        if st.button(f"Add to Cart {product[1]}"):
            cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (st.session_state.current_user[0], product[0], 1))
            conn.commit()
            st.success(f"Added {product[1]} to cart")

def products_page():
    st.markdown('<h1 class="centered-title">Products</h1>', unsafe_allow_html=True)
    search_query = st.text_input("Search products")
    if search_query:
        cursor.execute("SELECT id, name, price, is_popular, description FROM products WHERE name LIKE ? AND is_popular = 0", ('%'+search_query+'%',))
    else:
        cursor.execute("SELECT id, name, price, is_popular, description FROM products WHERE is_popular = 0")
    products = cursor.fetchall()
    for product in products:
        create_product_card(product)

def popular_products_page():
    st.markdown('<h1 class="centered-title">Popular Products</h1>', unsafe_allow_html=True)
    cursor.execute("SELECT id, name, price, is_popular, description FROM products WHERE is_popular = 1")
    popular_products = cursor.fetchall()
    for product in popular_products:
        create_product_card(product)

def update_cart_quantity(user_id, product_id, new_quantity):
    if new_quantity > 0:
        cursor.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?", (new_quantity, user_id, product_id))
    else:
        cursor.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    conn.commit()

def cart_page():
    st.markdown('<h1 class="centered-title">Cart</h1>', unsafe_allow_html=True)
    cursor.execute("""
        SELECT p.id, p.name, p.price, c.quantity 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ?
    """, (st.session_state.current_user[0],))
    cart_items = cursor.fetchall()
    
    total_cost = 0
    
    for index, item in enumerate(cart_items):
        product_id, name, price, quantity = item
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            # Image placeholder
            img = Image.new('RGB', (100, 100), color='gray')
            st.image(img, use_column_width=True)
        
        with col2:
            st.subheader(name)
            st.write(f"Price: ${price:.2f}")
            st.write(f"Quantity: {quantity}")
            st.write(f"Subtotal: ${price * quantity:.2f}")
        
        with col3:
            new_quantity = st.number_input(f"Update quantity for {name}", min_value=0, value=quantity, step=1, key=f"quantity_{index}_{product_id}")
            if new_quantity != quantity:
                update_cart_quantity(st.session_state.current_user[0], product_id, new_quantity)
                st.rerun()
        
        total_cost += price * quantity
        st.divider()
    
    st.subheader(f"Total Cost: ${total_cost:.2f}")
    
    if st.button("Purchase"):
        for item in cart_items:
            product_id, _, _, quantity = item
            cursor.execute("INSERT INTO purchases (user_id, product_id, quantity, date) VALUES (?, ?, ?, ?)",
            (st.session_state.current_user[0], product_id, quantity, datetime.datetime.now()))
        cursor.execute("DELETE FROM cart WHERE user_id = ?", (st.session_state.current_user[0],))
        conn.commit()
        st.success(f"Purchase successful! Total amount paid: ${total_cost:.2f}")
        st.balloons()

def user_home_page():
    st.markdown('<h1 class="centered-title">Welcome, {}</h1>'.format(st.session_state.current_user[1]), unsafe_allow_html=True)
    
    cursor.execute("SELECT id, name, price, description FROM products WHERE is_popular = 1 LIMIT 1")
    popular_product = cursor.fetchone()
    
    if popular_product:
        col1, col2 = st.columns(2)
        with col1:
            # Image placeholder
            img = Image.new('RGB', (400, 400), color='gray')
            st.image(img, use_column_width=True)
        with col2:
            st.subheader(popular_product[1])
            st.write(popular_product[3])  # Description
            st.write(f"Price: ${popular_product[2]:.2f}")
            if st.button("Add to Cart"):
                cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (st.session_state.current_user[0], popular_product[0], 1))
                conn.commit()
                st.success(f"Added {popular_product[1]} to cart")
    else:
        st.write("No popular products available at the moment.")

def hex_to_rgba(hex_code, alpha=1.0):
    hex_code = hex_code.lstrip('#')
    rgb = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"

def user_profile_page():
    st.markdown('<h1 class="centered-title">User Profile</h1>', unsafe_allow_html=True)
    st.write(f"Username: {st.session_state.current_user[1]}")
    st.write(f"Email: {st.session_state.current_user[3]}")
    st.subheader("Change Password")
    new_password = st.text_input("New Password", type="password")
    if st.button("Change Password"):
        change_password(new_password)
    color = st.color_picker("Pick A Color", "#371F76")
    st.write("The current color is", color)
    hex_code = color
    rgba_value = hex_to_rgba(hex_code, alpha=0.3)
    st.markdown(f"""
    <style>
    .stApp {{
        background-image: linear-gradient(135deg, {rgba_value}, transparent);
        backdrop-filter: blur(10px);
        color: white;
    }}
    </style>
    """, unsafe_allow_html=True)

def contact_page():
    st.markdown('<h1 class="centered-title">Contact Us</h1>', unsafe_allow_html=True)
    st.write("Address: 123 Main St, City, State 12345")
    st.write("Phone: (555) 123-4567")
    st.write("Instagram: @myapp_official")

def host_dashboard_page():
    st.markdown('<h1 class="centered-title">Host Dashboard</h1>', unsafe_allow_html=True)
    
    # Read data from database
    df = pd.read_sql_query("""
        SELECT p.name as Product, pu.date as Date, pu.quantity as Quantity, p.price as Price, u.username as Customer
        FROM purchases pu
        JOIN products p ON pu.product_id = p.id
        JOIN users u ON pu.user_id = u.id
    """, conn)
    
    df['Total'] = df['Quantity'] * df['Price']
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Sidebar filters
    st.sidebar.header("Please Filter Here:")
    product = st.sidebar.multiselect(
        "Select the Product:",
        options=df["Product"].unique(),
        default=df["Product"].unique()
    )

    customer = st.sidebar.multiselect(
        "Select the Customer:",
        options=df["Customer"].unique(),
        default=df["Customer"].unique(),
    )

    df_selection = df.query(
        "Product == @product & Customer == @customer"
    )

    # Check if the dataframe is empty:
    if df_selection.empty:
        st.warning("No data available based on the current filter settings!")
        st.stop() # This will halt the app from further execution.

    # TOP KPI's
    total_sales = int(df_selection["Total"].sum())
    average_sale_by_transaction = round(df_selection["Total"].mean(), 2)

    left_column, right_column = st.columns(2)
    with left_column:
        st.subheader("Total Sales:")
        st.subheader(f"US $ {total_sales:,}")
    with right_column:
        st.subheader("Average Sales Per Transaction:")
        st.subheader(f"US $ {average_sale_by_transaction}")

    st.markdown("""---""")

    # SALES BY PRODUCT [BAR CHART]
    sales_by_product = df_selection.groupby(by=["Product"])[["Total"]].sum().sort_values(by="Total")
    fig_product_sales = px.bar(
        sales_by_product,
        x="Total",
        y=sales_by_product.index,
        orientation="h",
        title="<b>Sales by Product</b>",
        color_discrete_sequence=["#0083B8"] * len(sales_by_product),
        template="plotly_white",
    )
    fig_product_sales.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=(dict(showgrid=False))
    )

    # SALES BY DATE [LINE CHART]
    sales_by_date = df_selection.groupby(by=["Date"])[["Total"]].sum()
    fig_daily_sales = px.line(
        sales_by_date,
        x=sales_by_date.index,
        y="Total",
        title="<b>Sales by Date</b>",
        color_discrete_sequence=["#0083B8"],
        template="plotly_white",
    )
    fig_daily_sales.update_layout(
        xaxis=dict(tickmode="linear"),
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=(dict(showgrid=False)),
    )

    left_column, right_column = st.columns(2)
    left_column.plotly_chart(fig_daily_sales, use_container_width=True)
    right_column.plotly_chart(fig_product_sales, use_container_width=True)

engine = create_engine('sqlite:///mydatabase.db')

def host_products_page():
    st.markdown('<h1 class="centered-title">Products and Purchases</h1>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Products", "Purchases", "Users"])

    with tab1:
        # Create a pandas dataframe for products
        products_df = pd.read_sql_table('products', engine)
        edited_df = st.data_editor(products_df, use_container_width=True, num_rows="dynamic")

        # Update the database with the edited dataframe
        if edited_df is not None:
            edited_df.to_sql('products', engine, if_exists='replace', index=False)
            st.success("Changes saved successfully!")

    with tab2:
        # Create a pandas dataframe for purchases
        purchases_df = pd.read_sql_table('purchases', engine)
        edited_df = st.data_editor(purchases_df, use_container_width=True, num_rows="dynamic")

        # Update the database with the edited dataframe
        if edited_df is not None:
            edited_df.to_sql('purchases', engine, if_exists='replace', index=False)
            st.success("Changes saved successfully!")
    
    with tab3:
        # Create a pandas dataframe for users
        users_df = pd.read_sql_table('users', engine)
        edited_df = st.data_editor(users_df, use_container_width=True, num_rows="dynamic")

        # Update the database with the edited dataframe
        if edited_df is not None:
            edited_df.to_sql('users', engine, if_exists='replace', index=False)
            st.success("Changes saved successfully!")

def host_profile_page():
    st.markdown('<h1 class="centered-title">Host Profile</h1>', unsafe_allow_html=True)
    st.write(f"Username: {st.session_state.current_host[1]}")
    st.subheader("Change Password")
    new_password = st.text_input("New Password", type="password")
    if st.button("Change Password"):
        change_host_password(new_password)
    color = st.color_picker("Pick A Color", "#371F76")
    st.write("The current color is", color)
    hex_code = color
    rgba_value = hex_to_rgba(hex_code, alpha=0.3)
    st.markdown(f"""
    <style>
    .stApp {{
        background-image: linear-gradient(135deg, {rgba_value}, transparent);
        backdrop-filter: blur(10px);
        color: white;
    }}
    </style>
    """, unsafe_allow_html=True)

# Main app logic
def main():
    if not st.session_state.current_user and not st.session_state.current_host:
        if st.session_state.page == "Login":
            login_page()
        elif st.session_state.page == "Sign Up":
            signup_page()
        elif st.session_state.page == "Forgot Password":
            forgot_password_page()
    elif st.session_state.current_host:
        tabs = st.tabs(["Dashboard", "Products and Purchases", "Profile", "Sign Out"])
        
        with tabs[0]:
            host_dashboard_page()
        with tabs[1]:
            host_products_page()
        with tabs[2]:
            host_profile_page()
        with tabs[3]:
            if st.button("Sign Out"):
                st.session_state.current_host = None
                st.session_state.page = "Login"
                st.rerun()
    else:
        tabs = st.tabs(["Home", "Products", "Popular", "Cart", "Profile", "Contact", "Sign Out"])
        
        with tabs[0]:
            user_home_page()
        with tabs[1]:
            products_page()
        with tabs[2]:
            popular_products_page()
        with tabs[3]:
            cart_page()
        with tabs[4]:
            user_profile_page()
        with tabs[5]:
            contact_page()
        with tabs[6]:
            if st.button("Sign Out"):
                st.session_state.current_user = None
                st.session_state.page = "Login"
                st.rerun()

if __name__ == "__main__":
    main()