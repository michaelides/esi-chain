import React from 'react';
import { useChatbotContext } from '@chainlit/react-client';

export default function LoginButton() {
  const { sendMessage } = useChatbotContext();

  console.log("LoginButton component loaded!"); // Add this line for debugging

  const handleLoginClick = () => {
    // Send a custom message to the backend to trigger the login
    sendMessage({
      content: 'login_trigger',
      elements: [],
      actions: []
    });
  };

  return (
    <div style={{ position: 'fixed', top: '10px', right: '20px', zIndex: 9999, backgroundColor: 'red', padding: '10px', border: '1px solid black' }}>
      <button
        id="login-button"
        style={{
          backgroundColor: 'yellow',
          color: 'black',
          padding: '10px 20px',
          border: 'none',
          borderRadius: '5px',
          cursor: 'pointer',
          fontSize: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}
        onClick={handleLoginClick}
      >
        SIMPLE TEST
      </button>
    </div>
  );
}