import React from 'react';

export default function TestPage({ message, data }) {
  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>تست Inertia.js</h1>
      <p>{message}</p>
      <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f0f0f0', borderRadius: '5px' }}>
        <h3>اطلاعات پروژه:</h3>
        <p><strong>نام:</strong> {data.name}</p>
        <p><strong>نسخه:</strong> {data.version}</p>
      </div>
      <button 
        onClick={() => alert('دکمه کار می‌کند!')}
        style={{ 
          marginTop: '20px', 
          padding: '10px 20px', 
          backgroundColor: '#007bff', 
          color: 'white', 
          border: 'none', 
          borderRadius: '5px',
          cursor: 'pointer'
        }}
      >
        کلیک کن
      </button>
    </div>
  );
}
