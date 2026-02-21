from utils import update_data, frame_html, live_html, days_html, months_html, records_html

def main_page():
    last_data_timestamp = update_data()
    print(f"Last data: {last_data_timestamp}")
    try:
        live_html_content = live_html()
    except Exception as e:
        live_html_content = f"Error loading live data: {e}"
    try:
        days_html_content = days_html()
    except Exception as e:
        days_html_content = f"Error loading days data: {e}"
    try:
        months_html_content = months_html()
    except Exception as e:
        months_html_content = f"Error loading months data: {e}"
    try:
        records_html_content = records_html()
    except Exception as e:
        records_html_content = f"Error loading records data: {e}"
    
    html_content = frame_html(live_html=live_html_content, days_html=days_html_content, months_html=months_html_content, records_html=records_html_content)
    # save if 
    with open("index.html", "w") as f:
        f.write(html_content)
    return html_content

html_content = main_page()

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("HTML generated successfully.")
