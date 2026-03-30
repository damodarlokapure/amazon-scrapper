from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import random
import time

TN_PINCODES = ["600001", "641001", "625001", "620001", "630001"]

def _scroll_until_settled(driver, max_rounds=8):
    """Scrolls down in chunks to trigger lazy-loaded offers."""
    last_height = 0
    stable_rounds = 0
    for _ in range(max_rounds):
        driver.execute_script("window.scrollBy(0, Math.floor(window.innerHeight * 0.9));")
        time.sleep(0.8)
        current_height = driver.execute_script("return document.body.scrollHeight")
        if current_height == last_height:
            stable_rounds += 1
            if stable_rounds >= 2:
                break
        else:
            stable_rounds = 0
        last_height = current_height
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.8)


def get_driver(proxy_url=None):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    if proxy_url:
        options.add_argument(f"--proxy-server={proxy_url}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def fetch_all_offers(asin: str, pincode: str = None, proxy_url: str = None, max_attempts: int = 3, sleep_between: float = 2.0):
    if not pincode:
        pincode = random.choice(TN_PINCODES)

    last_html = ""
    for attempt in range(1, max_attempts + 1):
        driver = get_driver(proxy_url=proxy_url)
        try:
            # Step 1  Load product page first (establishes session/cookies)
            product_url = f"https://www.amazon.in/dp/{asin}"
            driver.get(product_url)
            time.sleep(3)

            # Step 2  Now load with ?aod=1 to trigger All Offers Display
            aod_url = f"https://www.amazon.in/dp/{asin}?aod=1&condition=new"
            driver.get(aod_url)

            wait = WebDriverWait(driver, 20)

            # Step 3  Wait for the AOD offer list to fully render
            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#aod-offer, #aod-pinned-offer")
                    )
                )
                _scroll_until_settled(driver)
            except Exception:
                # Try clicking "See all buying options" button
                try:
                    btn = driver.find_element(
                        By.CSS_SELECTOR,
                        "#buybox-see-all-buying-choices a, "
                        "a[href*='aod=1'], "
                        "#aod-ingress-link"
                    )
                    btn.click()
                    time.sleep(4)
                    _scroll_until_settled(driver)
                except Exception:
                    pass

            # Step 4  Save rendered HTML for debug
            last_html = driver.page_source
            with open(f"selenium_output_{asin}.html", "w", encoding="utf-8") as f:
                f.write(last_html)

            # Basic ban/captcha detection
            if _looks_like_captcha(last_html):
                print(f"[Selenium] Attempt {attempt}/{max_attempts} captcha detected for ASIN={asin}; retrying...")
                continue

            # Step 5  Log what we found
            offers        = driver.find_elements(By.CSS_SELECTOR, "#aod-offer")
            pinned        = driver.find_elements(By.CSS_SELECTOR, "#aod-pinned-offer")
            seller_links  = driver.find_elements(By.CSS_SELECTOR, "a[href*='seller=']")
            prices        = driver.find_elements(By.CSS_SELECTOR, "span.a-price span.a-offscreen")

            print(
                f"[Selenium] ASIN={asin} attempt={attempt}/{max_attempts} | "
                f"pinned={len(pinned)} | offers={len(offers)} | sellers={len(seller_links)} | prices={len(prices)}"
            )

            # If no offers were found, retry once more before giving up
            if len(offers) + len(pinned) == 0 and attempt < max_attempts:
                time.sleep(sleep_between)
                continue

            return last_html, pincode

        except Exception as exc:
            print(f"[Selenium] Attempt {attempt}/{max_attempts} failed for ASIN={asin}: {exc}")
        finally:
            driver.quit()

        time.sleep(sleep_between)

    # Return last seen HTML (might be captcha/empty) so caller can attempt fallback parsing.
    return last_html, pincode


def _looks_like_captcha(html: str) -> bool:
    if not html:
        return False
    lowered = html.lower()
    return "enter the characters you see" in lowered or "type the characters you see" in lowered or "captcha" in lowered