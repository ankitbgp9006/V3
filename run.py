import base64

def _encode(text):
    b64 = base64.b64encode(text.encode()).decode()
    return ''.join(f"{ord(c):03d}" for c in b64)

if __name__ == "__main__":
    # Example usage
    api_url = input("Enter your API URL to encode: ").strip()
    encoded = _encode(api_url)
    print(f"\n🔐 Encoded (Triple-Digit) Output:\n{encoded}")
