import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime as dt
import pytz
import smtplib
from dotenv import dotenv_values

config = {
    **dotenv_values(".env.secret")
}

EMAIL = config["MY_EMAIL"]
PASSWORD = config["MY_PASSWORD"]

system_header = {
    "Accept-Language": config["ACCEPT_LANGUAGE"],
    "User-Agent": config["USER_AGENT"]
}

SCOPE = ['https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive"]

CREDS = ServiceAccountCredentials.from_json_keyfile_name(
    filename="Credentials.json",
    scopes=SCOPE
)

client = gspread.authorize(CREDS)
sheets_products = client.open("AmazonPriceTracker").worksheet("Products")
sheets_tracker = client.open("AmazonPriceTracker").worksheet("Tracker")

df = pd.DataFrame(sheets_products.get_all_records())
product_dict = df.to_dict()
unique_product = df["product_url"].unique()

IST = pytz.timezone('Asia/Kolkata')
today_ist = dt.datetime.now(IST)
today = today_ist.strftime("%d-%m-%Y")

user_url = st.text_input(
    label="Enter Amazon product url: ",
    placeholder="Enter"
)

set_price = st.number_input("Set the amount of the product to alert you : ₹")


def finding():
    """functions checks the product tile and price and returns it"""
    response = requests.get(url=user_url, headers=system_header)
    soup = BeautifulSoup(response.content, "html.parser")
    find_title = soup.find("span", id="productTitle")
    find_price = soup.find("span", class_="a-price-whole")

    try:
        return find_title.get_text().strip(), find_price.get_text().strip(".").replace(",", "")
    except AttributeError:
        return None


if set_price and user_url:
    finder = finding()

    while finder is None:
        finder = finding()

    title = finder[0]
    price_as_float = float(finder[1])

    sheets_data = {
        "name_of_the_product": title,
        "price": price_as_float,
        "date": str(today),
        "set_amount": set_price,
        "product_url": user_url
    }
    sheets_products.append_row(
        [
            sheets_data["name_of_the_product"],
            sheets_data["price"],
            sheets_data["date"],
            sheets_data["set_amount"],
            sheets_data["product_url"]
        ]
    )

    sheets_tracker.append_row(
        [
            sheets_data["name_of_the_product"],
            sheets_data["price"],
            sheets_data["date"]
        ]
    )

    st.write("\nyour product added in the database successfully,\nit will remind you when the value it's down👍")

"""Tracking the product"""
# This Tracker program run every day at 9:30 P.M IST

if today_ist.strftime('%H:%M:%S') == "09:30:00":

    def tracking(product_url):
        """functions checks the product tile and price and returns it"""
        try:
            response = requests.get(url=product_url, headers=system_header)
            soup = BeautifulSoup(response.content, "html.parser")
            find_title = soup.find("span", id="productTitle")
            find_price = soup.find("span", class_="a-price-whole")

            return find_title.get_text().strip(), find_price.get_text().strip(".").replace(",", "")

        except AttributeError:
            return None


    j = 0
    for i in unique_product:
        if i == "":
            continue
        else:
            pass
        finder = tracking(product_url=i)
        while finder is None:
            finder = tracking(product_url=i)

        title = finder[0]
        current_price = int(finder[1])

        sheets_data = {
            "name_of_the_product": title,
            "price": current_price,
            "date": str(today),
        }

        sheets_tracker.append_row(
            [
                sheets_data["name_of_the_product"],
                sheets_data["price"],
                sheets_data["date"],
            ]
        )

        set_price = product_dict["set_amount"][j]
        j += 1

        if current_price <= set_price:
            with smtplib.SMTP('smtp.gmail.com') as connection:
                connection.starttls()
                connection.login(EMAIL, PASSWORD)
                connection.sendmail(
                    from_addr=EMAIL,
                    to_addrs=EMAIL,  # here to_address for which person want to send
                    msg=f"Subject:From Amazon Tracker :O\n\nYour product {title} is now {set_price},"
                        f" Time is Counting, Don't Waste The Time To Buy it..."
                )
