/* public/login_inject.js
 * Adds a 🔐  icon to the top-right corner of any Chainlit page.
 * Sends the entered password to the backend via a hidden message.
 * Works with both the __ESI_LOGIN__ trick or native Chainlit basic-auth.
 *************************************************************/

document.addEventListener('DOMContentLoaded', () => {
  // run only once
  if (window.__esiLoginInjected) return;
  window.__esiLoginInjected = true;

  /* 1.  CSS for the floating button */
  const style = document.createElement('style');
  style.textContent = `
    #esi-login-btn {
      position: fixed;
      bottom: 20px;
      left: 15px;
      z-index: 9999;
  #    background: #2563eb;
      color: #fff;
      border: none;
      border-radius: 6px;
      padding: 6px 10px;
      font-size: 14px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
   #   box-shadow: 0 2px 4px rgba(0,0,0,.2);
    }
    #esi-login-btn:hover {
   #   background: #1e40af;
    }
    #esi-login-modal input:focus {
      outline: none;
      border-color: #2563eb;
      box-shadow: 0 0 3px rgba(37, 99, 235, 0.5);
    }
  `;
  document.head.appendChild(style);

  /* 2.  Create the button */
  const btn = document.createElement('button');
  btn.id = 'esi-login-btn';

  // Function to update the icon based on the theme
  function updateIcon() {
    // Check the value of the --background CSS variable
    const backgroundColor = getComputedStyle(document.documentElement).getPropertyValue('--background');
    const isLightTheme = backgroundColor && backgroundColor.startsWith('0 0% 100%'); // Assuming dark theme has a dark background

    const iconPath = isLightTheme ? '/public/login_light.svg' : '/public/login_dark.svg';
    btn.innerHTML = `<img src="${iconPath}" style="width: 25px; height: 25px; background-color: white; border: none;">`;
  }

  // Initial icon update
  updateIcon();

  // Observe changes to the body's class attribute to detect theme changes
  const observer = new MutationObserver(updateIcon);
  observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

  document.body.appendChild(btn);

 /* 3.  Click handler */
  btn.onclick = async () => {
    const username = prompt("Enter username:");
    const password = prompt("Enter password:");

    if (username && password) {
      window.chainlit.sendMessage(`/auth ${username} ${password}`);
    } else {
      alert("Login cancelled or incomplete.");
    }
  };



});