import socket
import sys
import ssl



def parse_url(url):
    """
    Manually parse a URL into its components. i.e, protocol, host, port, path.
    for example, given this "https://example.com:8080/path", it should return:
    ("https", "example.com", 8080, "/path")
    
     Params => url: string URL to parse
     Returns => tuple (protocol, host, port, path)
    """
    #default values
    protocol = "http"
    port = 80 # this isdefault port for http!
    path = "/"

    # 1. strip protocol if present!
    if "://" in url:
        protocol, url = url.split("://", 1)
        protocol = protocol.lower()
        rest = url
    else: 
        rest = url

    # 2. set default port based on protocol
    if protocol == "https":
        port = 443

    # 3. extract host and path
    if "/" in rest:
        host_port, path = rest.split("/", 1)
        path = "/" + path  # add leading slash
    else:
        host_port = rest
        path = "/"

    # 4. extract port if present ?
    if ":" in host_port:
        host, port_str = host_port.split(":", 1)
        port = int(port_str)
    else:
        host = host_port
    
    # 5. return valeus
    return protocol, host, port, path # returns a tuple of vals




def get_header_val(headers, key):
    """
    Given a list of HTTP headers, return the value for the given key.
    For example, given headers = ["Content-Type: text/html", "Content-Length: 1234"]
    and key = "Content-Length", it should return "1234".
    
     Params => headers: List of HTTP header strings
     Params => key: Header key to search for
     Returns => Value of the header or None if not found!
    """
    key_low = key.lower() # make key case-insensitive
    for header in headers: 
        if ":" in header:
            header_key, header_value = header.split(":", 1) # split only on first colon
            if header_key.strip().lower() == key_low:
                return header_value.strip()
    return None




def parse_cookies(headers):
    """
    Extracts cookie details from 'Set-Cookie' headers.
    Returns a list of dictionaries with name, expires, and domain.

    example header:
    Set-Cookie: sessionId=abc123; Expires=Wed, 24 Jun 2026 10:18:14 GMT; Domain=example67.com

    returns:
    [ {"name": "sessionId", "value": "abc123", "expires": "Wed, 24 Jun 2026 10:18:14 GMT", "domain": "example67.com"} ]

    param headers => List of HTTP header strings.
    returns => List of cookie dictionaries.
    """ 
    cookies =[]
    for header in headers:
        # Check for Set-Cookie header
        if header.lower().startswith("set-cookie:"):

            #format: Set-Cookie: name=value; Expires=expiry_date; Domain=domain_name
            cookie_str = header[len("set-cookie:"):].strip()
            parts = cookie_str.split(";")

            # First part is name=value
            name_value = parts[0].strip()

            # Extract name and value
            if "=" in name_value:
                name, value = name_value.split("=", 1)
                # Init cookie dictionary
                cookie = {"name": name.strip(), "value": value.strip(), "expires": None, "domain": None}

                # Process additional attributes
                for part in parts[1:]:
                    part = part.strip()
                    # Check for expires and domain
                    if part.lower().startswith("expires="):
                        cookie["expires"] = part[len("expires="):].strip()
                    elif part.lower().startswith("domain="):
                        cookie["domain"] = part[len("domain="):].strip()
                # Add cookie to list
                cookies.append(cookie)
    return cookies




def run_web_tester(url):
    """
    Main logic to connect, send request, handle redirects, and print info.

    Params => url: string URL to test.
    Returns => None, prints output directly.

    Steps:
        1. Connect to the server (handle HTTP and HTTPS)
        2. Send HTTP GET request
        3. Handle redirects (301, 302) up to a limit
        4. Check for HTTP/2 support via ALPN during SSL handshake
        5. Collect cookies from 'Set-Cookie' headers
        6. Check for password protection (401 Unauthorized)
        7. Print the final report

    """
    
    OG_url = url
    redir_count = 0
    max_redirects = 10  # Safety limit for infinite loops
    
    # State variables for final report
    h2_supported = "No"
    password_protected = "No"
    cookie_jar = []

    # Flag to avoid checking h2 multiple times
    h2_checked = False

    while redir_count < max_redirects:
        protocol, host, port, path = parse_url(url)
        
        # 1. Create a standard internet socket (i.e, TCP connection)!
        try:
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.settimeout(11) # 11s timeout
            
            # 2. Wrap for HTTPS (and check HTTP/2)
            if protocol == 'https':
                # Create SSL Context
                context = ssl.create_default_context()

                #LOGIC: We only need to check for h2 support once!
                # If we HAVE checked it (or if we detect it), we must force HTTP/1.1
                # Because, if we actually CONNECT with 'h2', we can't send text commands easily.
                # So if we detect h2, we note it, close the connection, and reconnect using HTTP/1.1.

                if not h2_checked:
                    # Ask the server if it speaks h2 or http/1.1
                    context.set_alpn_protocols(['h2', 'http/1.1'])
                else:
                    # We already know the answer, so force http/1.1 to retrieve data safely
                    context.set_alpn_protocols(['http/1.1'])

                try:
                    # Wrap the socket with encryption
                    connection = context.wrap_socket(connection, server_hostname=host)
                    sock = connection
                    sock.connect((host, port))

                    if not h2_checked:
                        # Check ALPN result for HTTP/2 support
                        negotiated_proto = sock.selected_alpn_protocol()
                        if negotiated_proto == 'h2':
                            h2_supported = "Yes!"
                            h2_checked = True

                           # We must close this connection and open a new one forced to 'http/1.1'
                           # because, We cannot send plain text over an 'h2' connection.
                            sock.close()
                            
                            # Recreate connection for HTTP/1.1
                            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            connection.settimeout(11)
                            
                            # Wrap again forcing http/1.1
                            context = ssl.create_default_context()
                            context.set_alpn_protocols(['http/1.1'])
                            sock = context.wrap_socket(connection, server_hostname=host)
                            sock.connect((host, port))
                        else:
                            #the server chose http/1.1, so we good to go!
                            h2_checked = True

                except ssl.SSLError as e:
                    print(f"SSL Error: {e}")
                    return
            else:
                # Plain HTTP connection
                connection.connect((host, port))
                sock = connection
            

            # 3. Send HTTP Request
            # Note => Even if server supports h2, we send HTTP/1.1 for compatibility!
            request = f"GET {path} HTTP/1.1\r\n"
            request += f"Host: {host}\r\n"
            request += "Connection: close\r\n"
            request += "\r\n" # End of headers
            
            sock.sendall(request.encode('utf-8')) # send request
            
            # 4. Receive Response
            response_data = b"" 
            while True:
                # Receive data in small blocks (4096 bytes)
                data = sock.recv(4096)
                if not data:
                    break
                response_data += data
            sock.close()
            
            # 5. Parse Response
            try:
                # Split Header and Body, seperated by a blank line \r\n\r\n
                if b'\r\n\r\n' in response_data:
                    header_part, body_part = response_data.split(b'\r\n\r\n', 1)
                else: 
                    # No body, only headers
                    header_part = response_data 
                    body_part = b"" 

                # Convert bytes to string to read headers
                header_text = header_part.decode('utf-8', errors='replace')
                header_lines = header_text.split('\r\n')
                
                # get the Status Code (e.g., 200, 301, 404), from the first line!
                status_line = header_lines[0]
                status_code = int(status_line.split(' ')[1])
                
                # Collect Cookies found in this response
                cookie_jar.extend(parse_cookies(header_lines))
                
                # Check Password Protection ?
                # 401 Unauthorized ===> password protection
                if status_code == 401:
                    password_protected = "Yes"

                # Check Redirects (status 301, 302)
                if status_code in [301, 302]:
                    new_location = get_header_val(header_lines, 'Location')
                    if new_location:
                        # Handle relative URLs in location
                        if not new_location.startswith('http'):
                            # Construct absolute URL
                            new_location = f"{protocol}://{host}{new_location}"
                        
                        # Update URL and loop
                        url = new_location
                        redir_count += 1
                        # We don't print "website: ..." yet, we follow the chain.
                        continue
                
                # If here, it's not a redirect, so good to go!
                break

            # handle errors
            except Exception as e:
                print(f"Error parsing response: {e}")
                break

        # Handle socket errors
        except socket.error as e:
            print(f"Connection ERROR!: {e}  ")
            return

    # 6. Final Output
    # Use the ORIGINAL host for the report, or the final one? 
    print(f"website: {OG_url.split('://')[-1] if '://' in OG_url else OG_url}") # use original URL for website
    print(f"1. Supports http2: {h2_supported}")  # Print HTTP/2 support
    print("2. List of Cookies:")                # Print cookies header

    # Print each cookie in given format!
    for cookie in cookie_jar:
        # Format: cookie name: <name>, expires time: <time>; domain name: <domain>
        output = f"cookie name: {cookie['name']}"
        if cookie['expires']:
            output += f", expires time: {cookie['expires']}"
        if cookie['domain']:
            output += f"; domain name: {cookie['domain']}"
        print(output)
    
    print(f"3. Password-protected: {password_protected}")




if __name__ == "__main__":
    # Check if user provided a URL in the command line
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        # IF not, ask for it!
        print("Please enter URL:")
        target_url = sys.stdin.readline().strip()


    if target_url:
        run_web_tester(target_url)



