from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt
import time

# Set up the Chrome driver path and options
driver_path = '/opt/homebrew/bin/chromedriver'  # Update this with your correct path
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Initialize the Chrome driver using Service
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=options)

# Load the page
driver.get("https://decisiondeskhq.com/results/2024/General/races/california-president-all-parties-general-election")

# Scroll down to the desired position
scroll_position = 1100  # Adjust this value based on where the content is located on the page
driver.execute_script(f"window.scrollTo(0, {scroll_position});")

# Wait for the page to load after scrolling
time.sleep(2)  # Adjust sleep time if necessary for the content to load

# Take screenshot and open with PIL
screenshot = driver.get_screenshot_as_png()
image = Image.open(BytesIO(screenshot))

# Display image to manually identify coordinates (method 2)
plt.imshow(image)
plt.title("Screenshot for Coordinate Selection")
plt.show()

# Cleanup
driver.quit()
