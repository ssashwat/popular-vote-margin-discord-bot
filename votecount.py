import time
import requests
import pytesseract
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
import re
from dotenv import load_dotenv
import os

load_dotenv()  # take environment variables from .env.

# Discord Webhook URL
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Manually specify the ChromeDriver path
CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"

# Chrome options setup
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run headless
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Initialize WebDriver with specified path
service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=chrome_options)

def get_vote_data_with_ocr():
    url = 'https://decisiondeskhq.com/results/2024/General/President/'
    try:
        driver.get(url)
        time.sleep(5)  # Wait for page to load fully
        print("HTML Loaded Successfully")
        
        # Scroll to the specified position
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)  # Wait for scrolling

        # Take a screenshot of the page
        screenshot = driver.get_screenshot_as_png()
        image = Image.open(BytesIO(screenshot))

        # Define coordinates for cropping based on provided values
        kamala_left, kamala_top, kamala_right, kamala_bottom = 428, 941, 602, 980
        trump_left, trump_top, trump_right, trump_bottom = 1718, 939, 1962, 981

        kamala_vote_image = image.crop((kamala_left, kamala_top, kamala_right, kamala_bottom))
        trump_vote_image = image.crop((trump_left, trump_top, trump_right, trump_bottom))

        kamala_votes_text = pytesseract.image_to_string(kamala_vote_image, config='--psm 6')
        trump_votes_text = pytesseract.image_to_string(trump_vote_image, config='--psm 6')

        print("OCR Result - Kamala Votes:", kamala_votes_text)
        print("OCR Result - Trump Votes:", trump_votes_text)

        kamala_votes = int(re.sub(r'\D', '', kamala_votes_text))
        trump_votes = int(re.sub(r'\D', '', trump_votes_text))
        
        return kamala_votes, trump_votes

    except WebDriverException as e:
        print("WebDriver encountered an issue:", str(e))
        return None, None

def calculate_margin(harris_votes, trump_votes):
    total_votes = harris_votes + trump_votes
    margin = ((trump_votes - harris_votes) / total_votes) * 100
    return round(margin, 5)

def send_text_to_discord(harris_votes, trump_votes, margin, prev_margin):
    # Determine margin change indicator
    if prev_margin is None:
        margin_indicator = "➖ **(First Report)**"
        circle_indicator = "🔘"  # Neutral color for the first report
    elif margin > prev_margin:
        margin_indicator = "🔺 **(Increased)**"
        circle_indicator = "🟢"  # Green for increase
    elif margin < prev_margin:
        margin_indicator = "🔻 **(Decreased)**"
        circle_indicator = "🔴"  # Red for decrease
    else:
        margin_indicator = "➖ **(Unchanged)**"
        circle_indicator = "⚪"  # Grey for no change

    # Prepare the message
    data = {
        "content": (
            f"**🇺🇸 2024 Presidential Vote Count 🇺🇸**\n\n"
            f"📅 **Timestamp:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
            f"**Candidate Vote Counts:**\n"
            f"- **Harris:** `{harris_votes:,}` votes\n"
            f"- **Trump:** `{trump_votes:,}` votes\n\n"
            f"**Overall Statistics:**\n"
            f"- **Total Votes Cast:** `{harris_votes + trump_votes:,}`\n"
            f"- **Harris Vote Share:** `{harris_votes / (harris_votes + trump_votes) * 100:.2f}%`\n"
            f"- **Trump Vote Share:** `{trump_votes / (harris_votes + trump_votes) * 100:.2f}%`\n"
            f"- **Lead Difference:** `{abs(trump_votes - harris_votes):,}` votes\n\n"
            f"**{circle_indicator} Win Margin:**  **{margin}%** {margin_indicator}"
        )
    }
    response = requests.post(WEBHOOK_URL, json=data)
    if response.status_code == 204:
        print("Successfully sent text update to Discord.")
    else:
        print("Failed to send text update to Discord:", response.status_code)


def send_screenshot_to_discord():
    # Take a screenshot of the specified section
    driver.get("https://decisiondeskhq.com/results/2024/General/races/california-president-all-parties-general-election")
    driver.execute_script("window.scrollTo(0, 1100);")  # Scroll down
    time.sleep(2)  # Wait for scrolling
    
    full_screenshot = driver.get_screenshot_as_png()
    img = Image.open(BytesIO(full_screenshot))
    cropped_screenshot = img.crop((169, 337, 1233, 1364))  # Crop to the specified area

    # Convert the cropped image to a format that can be sent as a file
    buffered = BytesIO()
    cropped_screenshot.save(buffered, format="PNG")
    buffered.seek(0)

    # Send the screenshot message separately
    files = {'file': ('screenshot.png', buffered, 'image/png')}
    response = requests.post(WEBHOOK_URL, files=files)
    if response.status_code == 204:
        print("Successfully sent screenshot to Discord.")
    else:
        print("Failed to send screenshot to Discord:", response.status_code)

def main():
    prev_margin = None
    while True:
        print("Fetching latest vote data with OCR...")
        harris_votes, trump_votes = get_vote_data_with_ocr()
        
        if harris_votes is not None and trump_votes is not None:
            margin = calculate_margin(harris_votes, trump_votes)
            print(f"Win Margin: {margin}%")
            send_text_to_discord(harris_votes, trump_votes, margin, prev_margin)
            send_screenshot_to_discord()  # Send screenshot after the text message
            prev_margin = margin  # Update previous margin for the next iteration
        else:
            print("Failed to fetch vote data using OCR.")
        
        # Wait for 3 minutes (180 seconds) before the next update
        print("Waiting for 3 minutes before the next update...")
        time.sleep(180)

if __name__ == "__main__":
    try:
        main()
    finally:
        driver.quit()
