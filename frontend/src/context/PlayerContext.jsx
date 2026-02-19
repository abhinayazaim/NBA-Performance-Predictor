import React, { createContext, useState, useContext } from 'react';

const PlayerContext = createContext();

export const PlayerProvider = ({ children }) => {
    const [selectedPlayerId, setSelectedPlayerId] = useState(null);

    return (
        <PlayerContext.Provider value={{ selectedPlayerId, setSelectedPlayerId }}>
            {children}
        </PlayerContext.Provider>
    );
};

export const usePlayerContext = () => useContext(PlayerContext);
