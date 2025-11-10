import Chat from './components/Chat';
import IngestionPanel from './components/IngestionPanel';
import './App.css';

const App = () => {
  return (
    <div className="app-shell">
      <div className="app-layout">
        <IngestionPanel />
        <Chat />
      </div>
    </div>
  );
};

export default App;
