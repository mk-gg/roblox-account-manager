"""
Roblox Authentication Module
Handles cookie validation, authentication tickets, and private server operations.
"""

import json
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse, parse_qs

import requests
import urllib3
from colorama import Fore, Style

# Disable SSL warnings for development
urllib3.disable_warnings()


class RobloxAuthError(Exception):
    """Custom exception for Roblox authentication errors."""
    pass


class RobloxAuth:
    """
    Handles Roblox authentication using cookies and provides methods for
    authentication tickets and private server operations.
    """
    
    BASE_HEADERS = {
        'User-Agent': 'Roblox/WinInet',
        'Referer': 'https://www.roblox.com/',
        'Origin': 'https://www.roblox.com',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive'
    }
    
    def __init__(self, cookie: str):
        """
        Initialize RobloxAuth with a cookie.
        
        Args:
            cookie: The .ROBLOSECURITY cookie value
        """
        self.cookie = cookie
        self.session = requests.Session()
        self.session.cookies['.ROBLOSECURITY'] = cookie
        self.session.headers.update(self.BASE_HEADERS)
    
    def get_csrf_token(self) -> Optional[str]:
        """
        Get CSRF token required for authenticated requests.
        
        Returns:
            CSRF token string or None if failed
        """
        try:
            response = self.session.post(
                'https://auth.roblox.com/v2/logout',
                verify=False,
                headers={'Content-Length': '0'}
            )
            
            csrf_token = response.headers.get('x-csrf-token')
            if csrf_token:
                return csrf_token
            
            print(f"{Fore.RED}Failed to get CSRF token. "
                  f"Status code: {response.status_code}")
            if response.text:
                print(f"{Fore.RED}Response: {response.text}")
            return None
            
        except Exception as e:
            print(f"{Fore.RED}Error getting CSRF token: {e}")
            return None
    
    def get_auth_ticket(self) -> Optional[str]:
        """
        Get authentication ticket for game joining.
        
        Returns:
            Authentication ticket string or None if failed
        """
        csrf_token = self.get_csrf_token()
        if not csrf_token:
            print(f"{Fore.RED}Failed to get CSRF token")
            return None
        
        try:
            headers = {
                'x-csrf-token': csrf_token,
                'Referer': 'https://www.roblox.com/games',
                'Origin': 'https://www.roblox.com',
                'Content-Type': 'application/json',
                'RBXAuthenticationNegotiation': '1'
            }
            
            response = self.session.post(
                'https://auth.roblox.com/v1/authentication-ticket',
                verify=False,
                headers=headers,
                json={}
            )
            
            # Debug information
            print(f"{Fore.CYAN}Auth ticket request status: {response.status_code}")
            print(f"{Fore.CYAN}Response headers:")
            for header, value in response.headers.items():
                print(f"{header}: {value}")
            
            if response.status_code in (200, 201):
                ticket = response.headers.get('rbx-authentication-ticket')
                if ticket:
                    return ticket
                print(f"{Fore.RED}Authentication ticket not found in response headers")
            else:
                print(f"{Fore.RED}Failed to get auth ticket. "
                      f"Status code: {response.status_code}")
                if response.text:
                    print(f"{Fore.RED}Response: {response.text}")
                    
        except Exception as e:
            print(f"{Fore.RED}Error getting auth ticket: {e}")
        
        return None
    
    def get_user_id(self) -> Optional[int]:
        """
        Get the authenticated user's ID.
        
        Returns:
            User ID as integer or None if failed
        """
        try:
            response = self.session.get(
                'https://users.roblox.com/v1/users/authenticated',
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json().get('id')
            
            print(f"{Fore.RED}Failed to get user ID. "
                  f"Status code: {response.status_code}")
            if response.text:
                print(f"{Fore.RED}Response: {response.text}")
                
        except Exception as e:
            print(f"{Fore.RED}Error getting user ID: {e}")
        
        return None
    
    def validate_cookie(self) -> bool:
        """
        Validate if the cookie is correct and working.
        
        Returns:
            True if cookie is valid, False otherwise
        """
        try:
            # Try the primary validation endpoint
            response = self.session.get(
                'https://users.roblox.com/v1/users/authenticated',
                headers={
                    'Accept': 'application/json',
                    'Cookie': f'.ROBLOSECURITY={self.cookie}'
                }
            )
            
            if response.status_code == 200:
                user_data = response.json()
                user_id = user_data.get('id', 'Unknown')
                print(f"{Fore.GREEN}Logged in as User ID: {user_id}")
                
                # Get username with a separate request
                self._get_username(user_id)
                return True
            
            # If primary endpoint fails, try backup endpoint
            if self._try_backup_validation():
                return True
            
            self._log_validation_failure(response)
            return False
            
        except Exception as e:
            print(f"{Fore.RED}Error validating cookie: {e}")
            return False
    
    def _get_username(self, user_id: int) -> None:
        """Get and display username for a user ID."""
        try:
            name_response = self.session.get(
                f'https://users.roblox.com/v1/users/{user_id}',
                headers={'Accept': 'application/json'}
            )
            if name_response.status_code == 200:
                username = name_response.json().get('name', 'Unknown')
                print(f"{Fore.GREEN}Username: {username}")
        except Exception:
            pass  # Silently fail for username lookup
    
    def _try_backup_validation(self) -> bool:
        """Try backup validation endpoint."""
        try:
            backup_response = self.session.get(
                'https://economy.roblox.com/v1/user/currency',
                headers={
                    'Accept': 'application/json',
                    'Cookie': f'.ROBLOSECURITY={self.cookie}'
                }
            )
            
            if backup_response.status_code == 200:
                print(f"{Fore.GREEN}Cookie validated successfully (backup method)")
                return True
                
        except Exception:
            pass
        
        return False
    
    def _log_validation_failure(self, response: requests.Response) -> None:
        """Log validation failure details."""
        print(f"{Fore.RED}Cookie validation failed")
        print(f"{Fore.RED}Status code: {response.status_code}")
        
        if response.text:
            try:
                error_data = response.json()
                print(f"{Fore.RED}Error: {json.dumps(error_data, indent=2)}")
            except (json.JSONDecodeError, ValueError):
                pass  # Not JSON response
    
    def get_server_info_from_code(self, code: str) -> Optional[Tuple[str, str]]:
        """
        Get place ID from server code directly.
        
        Args:
            code: Private server code
            
        Returns:
            Tuple of (place_id, private_server_link) or None if failed
        """
        try:
            csrf_token = self.get_csrf_token()
            if not csrf_token:
                print(f"{Fore.RED}Failed to get CSRF token")
                return None
            
            response = self.session.get(
                f'https://games.roblox.com/v1/games/server-link-code/{code}',
                headers={
                    'Accept': 'application/json',
                    'Referer': 'https://www.roblox.com/',
                    'x-csrf-token': csrf_token
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                place_id = data.get('placeId')
                
                if place_id:
                    place_id_str = str(place_id)
                    private_server_link = (
                        f"https://www.roblox.com/games/{place_id_str}"
                        f"?privateServerLinkCode={code}"
                    )
                    print(f"{Fore.GREEN}Found private server for "
                          f"place ID: {place_id_str}")
                    return (place_id_str, private_server_link)
            
            print(f"{Fore.RED}Failed to get private server info. "
                  f"Status code: {response.status_code}")
            if response.text:
                print(f"{Fore.RED}Response: {response.text}")
            return None
            
        except Exception as e:
            print(f"{Fore.RED}Error getting server info: {e}")
            return None
    
    def verify_private_server_access(self, place_id: str, 
                                   private_server_code: str) -> bool:
        """
        Verify if the user has access to the private server.
        
        Args:
            place_id: Roblox place ID
            private_server_code: Private server code
            
        Returns:
            True if access is verified, False otherwise
        """
        try:
            csrf_token = self.get_csrf_token()
            if not csrf_token:
                print(f"{Fore.RED}Failed to get CSRF token")
                return False
            
            response = self.session.get(
                f'https://games.roblox.com/v1/games/{place_id}/'
                f'private-servers/{private_server_code}',
                headers={
                    'Accept': 'application/json',
                    'Referer': 'https://www.roblox.com/',
                    'x-csrf-token': csrf_token
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('active') is True:
                    print(f"{Fore.GREEN}Private server access verified!")
                    return True
                else:
                    print(f"{Fore.RED}Private server is not active")
                    return False
                    
            elif response.status_code == 401:
                self._log_unauthorized_access()
                return False
            else:
                print(f"{Fore.RED}Failed to verify private server access. "
                      f"Status code: {response.status_code}")
                if response.text:
                    print(f"{Fore.RED}Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}Error verifying private server access: {e}")
            return False
    
    def _log_unauthorized_access(self) -> None:
        """Log unauthorized private server access information."""
        print(f"{Fore.RED}Not authorized to join this private server")
        print(f"{Fore.YELLOW}This could mean:")
        print("1. The private server link has expired")
        print("2. You're not whitelisted for this private server")
        print("3. The private server was created by a different account")
    
    def get_private_server_info(self, 
                              private_server_link_or_code: str) -> Optional[Tuple[str, str]]:
        """
        Get place ID and access code from private server link or code.
        
        Args:
            private_server_link_or_code: Private server link or code
            
        Returns:
            Tuple of (place_id, server_code) or None if failed
        """
        try:
            # If input is just a code, treat it as a server code
            if self._is_server_code(private_server_link_or_code):
                return self.get_server_info_from_code(private_server_link_or_code)
            
            parsed = urlparse(private_server_link_or_code)
            
            # Handle new share link format
            if self._is_share_link(parsed, private_server_link_or_code):
                return self._handle_share_link(parsed, private_server_link_or_code)
            
            # Handle old direct private server links
            elif 'privateServerLinkCode=' in private_server_link_or_code:
                return self._handle_direct_link(parsed, private_server_link_or_code)
            
            else:
                print(f"{Fore.RED}Invalid private server link format")
                return None
                
        except Exception as e:
            print(f"{Fore.RED}Error getting private server info: {e}")
            return None
    
    def _is_server_code(self, input_string: str) -> bool:
        """Check if input is just a server code."""
        return '/' not in input_string and '?' not in input_string
    
    def _is_share_link(self, parsed: urlparse, link: str) -> bool:
        """Check if this is a share link format."""
        return ('share' in parsed.path and 
                'code=' in link and 
                'type=Server' in link)
    
    def _handle_share_link(self, parsed: urlparse, 
                          link: str) -> Optional[Tuple[str, str]]:
        """Handle share link format."""
        query_params = parse_qs(parsed.query)
        
        if 'code' not in query_params:
            print(f"{Fore.RED}Invalid share link - no code found")
            return None
        
        code = query_params['code'][0]
        csrf_token = self.get_csrf_token()
        
        if not csrf_token:
            print(f"{Fore.RED}Failed to get CSRF token")
            return None
        
        response = self.session.get(
            f'https://games.roblox.com/v1/games/server-link-code/{code}',
            headers={
                'Accept': 'application/json',
                'Referer': 'https://www.roblox.com/',
                'x-csrf-token': csrf_token
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            place_id = data.get('placeId')
            
            if place_id:
                place_id_str = str(place_id)
                print(f"{Fore.GREEN}Found private server for "
                      f"place ID: {place_id_str}")
                return (place_id_str, code)
        
        print(f"{Fore.RED}Failed to get private server info. "
              f"Status code: {response.status_code}")
        if response.text:
            print(f"{Fore.RED}Response: {response.text}")
        return None
    
    def _handle_direct_link(self, parsed: urlparse, 
                           link: str) -> Optional[Tuple[str, str]]:
        """Handle direct private server links."""
        # Extract place ID from path
        path_parts = parsed.path.split('/')
        place_id = None
        
        for part in path_parts:
            if part.isdigit():
                place_id = part
                break
        
        if not place_id:
            print(f"{Fore.RED}Could not find place ID in private server link")
            return None
        
        # Extract server code
        server_code = link.split('privateServerLinkCode=')[1].split('&')[0]
        
        # Verify access before returning
        if not self.verify_private_server_access(place_id, server_code):
            return None
        
        print(f"{Fore.GREEN}Found private server for place ID: {place_id}")
        return (place_id, server_code)
    
    def get_join_script(self, place_id: str) -> Optional[str]:
        """
        Get the join script from PlaceLauncher.
        
        Args:
            place_id: Roblox place ID
            
        Returns:
            Join script string or None if failed
        """
        try:
            csrf_token = self.get_csrf_token()
            if not csrf_token:
                print(f"{Fore.RED}Failed to get CSRF token")
                return None
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'Roblox/WinInet',
                'Referer': 'https://www.roblox.com/',
                'Origin': 'https://www.roblox.com',
                'x-csrf-token': csrf_token,
                'Cookie': f'.ROBLOSECURITY={self.cookie}'
            }
            
            response = self.session.post(
                'https://gamejoin.roblox.com/v1/join-game',
                headers=headers,
                json={'placeId': place_id}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"{Fore.CYAN}Join script response: "
                      f"{json.dumps(data, indent=2)}")
                return data.get('joinScript')
            else:
                print(f"{Fore.RED}Failed to get join script. "
                      f"Status code: {response.status_code}")
                if response.text:
                    print(f"{Fore.RED}Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"{Fore.RED}Error getting join script: {e}")
            return None
    
    def get_private_server_join_script(self, place_id: str, 
                                     private_server_code: str) -> Optional[Dict[str, Any]]:
        """
        Get join script for private server.
        
        Args:
            place_id: Roblox place ID
            private_server_code: Private server code
            
        Returns:
            Join script data dictionary or None if failed
        """
        try:
            csrf_token = self.get_csrf_token()
            if not csrf_token:
                print(f"{Fore.RED}Failed to get CSRF token")
                return None
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'x-csrf-token': csrf_token,
                'Origin': 'https://www.roblox.com',
                'Referer': f'https://www.roblox.com/games/{place_id}',
                'User-Agent': 'Roblox/WinInet',
                'RBXAuthenticationNegotiation': '1'
            }
            
            payload = {
                'placeId': int(place_id),
                'isVipServer': True,
                'vipServerId': private_server_code,
                'gameId': None
            }
            
            join_response = self.session.post(
                'https://gamejoin.roblox.com/v1/join-game',
                headers=headers,
                json=payload
            )
            
            print(f"{Fore.CYAN}Join request status: {join_response.status_code}")
            if join_response.text:
                print(f"{Fore.CYAN}Join response: {join_response.text}")
            
            if join_response.status_code == 200:
                join_data = join_response.json()
                
                if join_data.get('joinScript'):
                    print(f"{Fore.GREEN}Successfully got join script")
                    return join_data
                else:
                    print(f"{Fore.RED}No join script in response")
                    print(f"{Fore.CYAN}Full response data: "
                          f"{json.dumps(join_data, indent=2)}")
            else:
                print(f"{Fore.RED}Failed to join. "
                      f"Status code: {join_response.status_code}")
                if join_response.text:
                    print(f"{Fore.RED}Response: {join_response.text}")
            
            return None
            
        except Exception as e:
            print(f"{Fore.RED}Error getting join script: {e}")
            return None