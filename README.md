# **My Project**

## **📌 Description**
This project provides tools for supporting model based question answering. These include questions on action and function level queries (Why is A in the plan, Why is F so high). It also allows MAST (multi-agent spatial temporal) models to be extended with additional concepts, including measuring the distance travelled by moving objects, and measuring the duration that two object (one moving, one stationary) are close. These measures are added to the model and can therefore be used in the queries for functions.

---

## **🚀 Installation**

### **1️⃣ Install with `pip` **
After cloning the repository, navigate into the project folder and install it:
```sh
pip install -e .
```
This installs dependencies (`Shapely`, `NetworkX`, etc.) automatically.

---

## **▶️ Usage**

Run the main script:
```sh
python3 main.py
```

Example usage inside Python:
```python
from xaip_tools import main
main()
```

---

## **📄 License**
📜 MIT License.


