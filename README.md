# Group 2: Full-Stack QR Generator

A sophisticated, secure, and high-performance QR code management system. This project serves as a comprehensive demonstration of integrating a **Python-based frontend (Streamlit)** with a **robust relational database (PostgreSQL)**, all optimized for the **Ubuntu 22.04.5 LTS** server environment.
visit us on -> https://barometer-stuffy-avenue.ngrok-free.dev/

### Deployment & Remote Access
This application is designed and tested to run on **Ubuntu 22.04.5 LTS**, utilizing a high-performance stack for local or cloud-based server hosting. Remote management is handled via **SSH**, and the application is exposed to the public internet using **ngrok** for secure, low-latency tunneling without complex firewall configurations.

---

## Features

* **Secure User Lifecycle:** Fully implemented Signup and Login system using `bcrypt` for industry-standard password hashing.
* **Dynamic QR Engine:** Generates high-fidelity QR codes in-memory for maximum speed, bypassing slow disk I/O.
* **Intelligent Validation:** A real-time, interactive password strength meter to ensure user security compliance.
* **Persistent Storage:** Full CRUD (Create, Read, Delete) capabilities for QR codes, with images stored as Base64 strings within PostgreSQL.
* **Modern UI/UX:** Features a sleek, responsive interface with **Lottie animations** and a mobile-friendly layout.
* **Asset Management:** A dedicated "My QR Codes" dashboard allowing users to view history and download codes as `.png` files.

---

## Technical Stack

| Component | Technology |
| :--- | :--- |
| **Operating System** | **Ubuntu 22.04.5 LTS** |
| **Frontend Framework** | Streamlit |
| **Styling & Layout** | **Custom CSS (Markdown Injection)** |
| **Primary Database** | PostgreSQL |
| **Security/Hashing** | Bcrypt |
| **QR Generation** | Python `qrcode` + `Pillow` |
| **Asset Storage** | Base64 Encoding |
| **Remote Access** | SSH (Secure Shell) |
| **Public Tunneling** | Ngrok |

---

## Architecture Overview

The application follows a modular architecture to ensure scalability and ease of maintenance:

1. **Authentication Layer:** Validates user credentials against hashed records before granting session access.
2. **Logic Layer:** Handles the translation of URLs or text into matricized QR data.
3. **Data Layer:** Manages relational links between users and their generated assets, ensuring that users only see their own history.
4. **Networking Layer:**
    * **SSH:** Provides a secure channel for developers to manage the server and database remotely.
    * **Ngrok:** Acts as the ingress point, tunneling the local Streamlit port (8501) to a public URL for external testing and usage.

---

## Contributors
* **Belarmino, Katrisha C.** — *System Architect*
* **De Torres, Yuan Kendrix B.** — *Application Developer*

> **Note:** This project was developed as a collaborative effort to bridge the gap between simple script-based tools and production-ready web applications.
