import Navbar from "./Navbar";
import About from "./pages/About";
import Test from "./pages/Test";
import Home from "./pages/Home";
import { Route, Routes } from "react-router-dom"
// Importing modules
function App() {
	return (
	<>
	<Navbar />
	<div className="container">
		<Routes>
			<Route path="/" element={<Home />} />
			<Route path="/test" element={<Test />} />
			<Route path="/current_bet" element={<About />} />

		</Routes>
	</div>
	</>
)
}
export default App
