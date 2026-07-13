import React, { createContext, useContext, useState } from 'react';

const StoreContext = createContext();

export const StoreProvider = ({ children }) => {
  const [user, setUser] = useState({ name: 'Admin', role: 'administrator' });
  const [loading, setLoading] = useState(false);

  return (
    <StoreContext.Provider value={{ user, setUser, loading, setLoading }}>
      {children}
    </StoreContext.Provider>
  );
};

export const useStore = () => useContext(StoreContext);
