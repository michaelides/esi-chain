import { make  } from "@chainlit/react-builder";

// Define the custom element for follow-up suggestions
// This component will receive the 'suggestions' prop from the backend
make(
  'FollowUpSuggestions',
  (props: { suggestions: string[] }) => {
    const { suggestions } = props;

    // Function to handle a suggestion click
    const handleSuggestionClick = (suggestion: string) => {
      // This sends the suggestion back to the chat input
      // You might want to also send it as a message or trigger an action
      window.postMessage({
        type: 'set_input',
        value: suggestion,
      }, '*');
    };

    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            onClick={() => handleSuggestionClick(suggestion)}
            style={{
              padding: '8px 12px',
              borderRadius: '20px',
              border: '1px solid #ccc',
              background: '#f0f0f0',
              cursor: 'pointer',
              fontSize: '14px',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              maxWidth: '200px', // Limit width to prevent very long buttons
            }}
          >
            {suggestion}
          </button>
        ))}
      </div>
    );
  }
);
