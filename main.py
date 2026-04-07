# """
# ArtCraft Backend — FastAPI + MongoDB (PyMongo) + Stripe + Groq AI
# """

# from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from pydantic import BaseModel
# from typing import List, Optional
# import hashlib, uuid, os, stripe, httpx
# from datetime import datetime
# from pymongo import MongoClient
# from bson import ObjectId
# from dotenv import load_dotenv

# load_dotenv()

# app = FastAPI(title="ArtCraft API", version="1.0.0")
# app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
#                    allow_methods=["*"], allow_headers=["*"])

# os.makedirs("uploads", exist_ok=True)
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
# client    = MongoClient(MONGO_URL)
# db        = client["artcraft"]

# users_col     = db["users"]
# artworks_col  = db["artworks"]
# tutorials_col = db["tutorials"]
# orders_col    = db["orders"]
# payments_col  = db["payments"]
# jobs_col      = db["jobs"]
# messages_col  = db["messages"]
# notifs_col    = db["notifications"]

# stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
# # FRONTEND_URL   = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")
# GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
# GROQ_CHAT_URL  = "https://api.groq.com/openai/v1/chat/completions"
# GROQ_MODEL     = "llama-3.1-8b-instant"
# ARTCRAFT_AI_SYSTEM = ("You are ArtCraft AI, a helpful assistant for Indian artists. "
#     "Help with artwork pricing, writing bios, getting more buyers, marketing on social media, "
#     "creating tutorials, dealing with brand collaborations, and running an art business in India. "
#     "Be concise, friendly, practical. Keep responses under 150 words. Use simple English.")

# def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
# def make_token(uid):  return hashlib.sha256(f"{uid}{uuid.uuid4()}".encode()).hexdigest()
# def to_str_id(doc):
#     if doc and "_id" in doc: doc["_id"] = str(doc["_id"])
#     return doc

# def get_current_user(request: Request):
#     auth = request.headers.get("Authorization", "")
#     if not auth.startswith("Bearer "): raise HTTPException(401, "Not authenticated")
#     user = users_col.find_one({"session_token": auth[7:]})
#     if not user: raise HTTPException(401, "Invalid or expired token")
#     return user

# def save_upload(file: UploadFile) -> str:
#     ext = os.path.splitext(file.filename)[1] if file.filename else ""
#     fp  = os.path.join("uploads", f"{uuid.uuid4()}{ext}")
#     with open(fp, "wb") as f: f.write(file.file.read())
#     return fp

# def push_notification(user_id: str, text: str):
#     notifs_col.insert_one({"user_id": user_id, "text": text, "read": False,
#                             "created_at": datetime.utcnow().isoformat()})

# # ── AUTH ──────────────────────────────────────────────────────
# @app.post("/auth/signup")
# def signup(first_name: str=Form(...), last_name: str=Form(...), email: str=Form(...),
#            password: str=Form(...), role: str=Form(...)):
#     email = email.lower().strip()
#     if users_col.find_one({"email": email, "role": role}):
#         raise HTTPException(400, "Account already exists for this email + role")
#     user = {"first_name": first_name, "last_name": last_name, "email": email,
#             "password_hash": hash_password(password), "role": role, "session_token": None,
#             "avatar_url": None, "cover_url": None, "created_at": datetime.utcnow().isoformat(),
#             "medium": "", "city": "", "bio": "", "skills": [], "instagram": "", "website": "",
#             "brand_name": "", "industry": "", "stripe_key": "", "upi": "", "bank_account": "", "ifsc": ""}
#     result = users_col.insert_one(user)
#     token  = make_token(str(result.inserted_id))
#     users_col.update_one({"_id": result.inserted_id}, {"$set": {"session_token": token}})
#     return {"token": token, "user_id": str(result.inserted_id), "role": role,
#             "name": f"{first_name} {last_name}", "email": email}

# @app.post("/auth/login")
# def login(email: str=Form(...), password: str=Form(...), role: str=Form(...)):
#     email = email.lower().strip()
#     user  = users_col.find_one({"email": email, "role": role})
#     if not user or user["password_hash"] != hash_password(password):
#         raise HTTPException(401, "Incorrect email, password, or role")
#     token = make_token(str(user["_id"]))
#     users_col.update_one({"_id": user["_id"]}, {"$set": {"session_token": token}})
#     return {"token": token, "user_id": str(user["_id"]), "role": user["role"],
#             "name": f"{user['first_name']} {user['last_name']}", "email": user["email"]}

# @app.post("/auth/logout")
# def logout(current_user=Depends(get_current_user)):
#     users_col.update_one({"_id": current_user["_id"]}, {"$set": {"session_token": None}})
#     return {"message": "Logged out"}

# @app.get("/auth/me")
# def get_me(current_user=Depends(get_current_user)):
#     return to_str_id({**current_user, "password_hash": "[hidden]"})

# # ── PROFILE ───────────────────────────────────────────────────
# @app.put("/profile")
# def update_profile(first_name: Optional[str]=Form(None), last_name: Optional[str]=Form(None),
#     medium: Optional[str]=Form(None), city: Optional[str]=Form(None), bio: Optional[str]=Form(None),
#     instagram: Optional[str]=Form(None), website: Optional[str]=Form(None),
#     brand_name: Optional[str]=Form(None), industry: Optional[str]=Form(None),
#     phone: Optional[str]=Form(None), upi: Optional[str]=Form(None),
#     bank_account: Optional[str]=Form(None), ifsc: Optional[str]=Form(None),
#     avatar: Optional[UploadFile]=File(None), cover: Optional[UploadFile]=File(None),
#     current_user=Depends(get_current_user)):
#     update = {}
#     for k, v in {"first_name": first_name, "last_name": last_name, "medium": medium,
#                   "city": city, "bio": bio, "instagram": instagram, "website": website,
#                   "brand_name": brand_name, "industry": industry, "phone": phone,
#                   "upi": upi, "bank_account": bank_account, "ifsc": ifsc}.items():
#         if v is not None: update[k] = v
#     if avatar: update["avatar_url"] = "/" + save_upload(avatar)
#     if cover:  update["cover_url"]  = "/" + save_upload(cover)
#     if update: users_col.update_one({"_id": current_user["_id"]}, {"$set": update})
#     return to_str_id({**users_col.find_one({"_id": current_user["_id"]}), "password_hash": "[hidden]"})

# @app.post("/profile/skills")
# def add_skill(skill: str=Form(...), current_user=Depends(get_current_user)):
#     users_col.update_one({"_id": current_user["_id"]}, {"$addToSet": {"skills": skill}})
#     return {"message": "Skill added"}

# @app.delete("/profile/skills/{skill}")
# def remove_skill(skill: str, current_user=Depends(get_current_user)):
#     users_col.update_one({"_id": current_user["_id"]}, {"$pull": {"skills": skill}})
#     return {"message": "Skill removed"}

# # ── ARTWORKS ──────────────────────────────────────────────────
# @app.post("/artworks")
# def create_artwork(title: str=Form(...), price: float=Form(...), medium: str=Form("Other"),
#     dims: str=Form(""), desc: str=Form(""), status: str=Form("draft"),
#     image: Optional[UploadFile]=File(None), current_user=Depends(get_current_user)):
#     if current_user["role"] != "artist": raise HTTPException(403, "Only artists can upload artworks")
#     image_url = ("/" + save_upload(image)) if image else None
#     artwork = {"artist_id": str(current_user["_id"]),
#                "artist_name": f"{current_user['first_name']} {current_user['last_name']}",
#                "artist_avatar": current_user.get("avatar_url"), "title": title, "price": price,
#                "medium": medium, "dims": dims, "desc": desc, "status": status,
#                "image_url": image_url, "created_at": datetime.utcnow().isoformat()}
#     result = artworks_col.insert_one(artwork)
#     artwork["_id"] = str(result.inserted_id)
#     return artwork

# @app.get("/artworks")
# def list_artworks(status: Optional[str]=None, medium: Optional[str]=None,
#                   artist_id: Optional[str]=None, search: Optional[str]=None):
#     query = {"status": status or "listed"}
#     if medium:    query["medium"]    = medium
#     if artist_id: query["artist_id"] = artist_id
#     if search:
#         query["$or"] = [{"title": {"$regex": search, "$options": "i"}},
#                         {"artist_name": {"$regex": search, "$options": "i"}},
#                         {"medium": {"$regex": search, "$options": "i"}}]
#     return [to_str_id(a) for a in artworks_col.find(query).sort("created_at", -1)]

# @app.get("/artworks/mine")
# def my_artworks(current_user=Depends(get_current_user)):
#     return [to_str_id(a) for a in artworks_col.find({"artist_id": str(current_user["_id"])}).sort("created_at", -1)]

# @app.get("/artworks/{artwork_id}")
# def get_artwork(artwork_id: str):
#     try: art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
#     except: raise HTTPException(404, "Artwork not found")
#     if not art: raise HTTPException(404, "Artwork not found")
#     return to_str_id(art)

# @app.put("/artworks/{artwork_id}")
# def update_artwork(artwork_id: str, title: Optional[str]=Form(None), price: Optional[float]=Form(None),
#     medium: Optional[str]=Form(None), dims: Optional[str]=Form(None), desc: Optional[str]=Form(None),
#     status: Optional[str]=Form(None), image: Optional[UploadFile]=File(None),
#     current_user=Depends(get_current_user)):
#     try: art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
#     except: raise HTTPException(404, "Not found")
#     if not art or art["artist_id"] != str(current_user["_id"]): raise HTTPException(403, "Not your artwork")
#     update = {k: v for k, v in {"title": title, "price": price, "medium": medium,
#                                   "dims": dims, "desc": desc, "status": status}.items() if v is not None}
#     if image: update["image_url"] = "/" + save_upload(image)
#     if update: artworks_col.update_one({"_id": ObjectId(artwork_id)}, {"$set": update})
#     return to_str_id(artworks_col.find_one({"_id": ObjectId(artwork_id)}))

# @app.delete("/artworks/{artwork_id}")
# def delete_artwork(artwork_id: str, current_user=Depends(get_current_user)):
#     try: art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
#     except: raise HTTPException(404, "Not found")
#     if not art or art["artist_id"] != str(current_user["_id"]): raise HTTPException(403, "Not your artwork")
#     artworks_col.delete_one({"_id": ObjectId(artwork_id)})
#     return {"message": "Deleted"}

# # ── TUTORIALS ─────────────────────────────────────────────────
# @app.post("/tutorials")
# def create_tutorial(title: str=Form(...), price: float=Form(...), duration: str=Form(""),
#     level: str=Form("Beginner"), lang: str=Form("English"), desc: str=Form(""),
#     video: Optional[UploadFile]=File(None), thumb: Optional[UploadFile]=File(None),
#     current_user=Depends(get_current_user)):
#     if current_user["role"] != "artist": raise HTTPException(403, "Only artists can create tutorials")
#     tutorial = {"artist_id": str(current_user["_id"]),
#                 "artist_name": f"{current_user['first_name']} {current_user['last_name']}",
#                 "artist_avatar": current_user.get("avatar_url"), "title": title, "price": price,
#                 "duration": duration, "level": level, "lang": lang, "desc": desc,
#                 "video_url": ("/" + save_upload(video)) if video else None,
#                 "thumb_url": ("/" + save_upload(thumb)) if thumb else None,
#                 "students": 0, "earnings": 0.0, "created_at": datetime.utcnow().isoformat()}
#     result = tutorials_col.insert_one(tutorial)
#     tutorial["_id"] = str(result.inserted_id)
#     return tutorial

# @app.get("/tutorials")
# def list_tutorials(artist_id: Optional[str]=None):
#     query = {"artist_id": artist_id} if artist_id else {}
#     tuts = []
#     for t in tutorials_col.find(query).sort("created_at", -1):
#         t = to_str_id(t); t.pop("video_url", None); tuts.append(t)
#     return tuts

# @app.get("/tutorials/mine/purchased")
# def my_purchased_tutorials(current_user=Depends(get_current_user)):
#     paid = payments_col.find({"user_id": str(current_user["_id"]), "status": "completed", "type": "tutorial"})
#     tuts = []
#     for p in paid:
#         try:
#             tut = tutorials_col.find_one({"_id": ObjectId(p["tutorial_id"])})
#             if tut: tuts.append(to_str_id(tut))
#         except: pass
#     return tuts

# @app.get("/tutorials/{tutorial_id}")
# def get_tutorial(tutorial_id: str, request: Request):
#     try: tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
#     except: raise HTTPException(404, "Not found")
#     if not tut: raise HTTPException(404, "Not found")
#     tut = to_str_id(tut)
#     auth = request.headers.get("Authorization", "")
#     current_user = users_col.find_one({"session_token": auth[7:]}) if auth.startswith("Bearer ") else None
#     user_id  = str(current_user["_id"]) if current_user else None
#     is_owner = user_id and user_id == tut["artist_id"]
#     has_bought = bool(payments_col.find_one({"user_id": user_id, "tutorial_id": tutorial_id,
#                                               "status": "completed"})) if user_id else False
#     if not is_owner and not has_bought:
#         tut.pop("video_url", None); tut["locked"] = True
#     else:
#         tut["locked"] = False
#     return tut

# @app.delete("/tutorials/{tutorial_id}")
# def delete_tutorial(tutorial_id: str, current_user=Depends(get_current_user)):
#     try: tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
#     except: raise HTTPException(404, "Not found")
#     if not tut or tut["artist_id"] != str(current_user["_id"]): raise HTTPException(403, "Not your tutorial")
#     tutorials_col.delete_one({"_id": ObjectId(tutorial_id)})
#     return {"message": "Deleted"}

# # ── PAYMENTS — ARTWORK (PaymentIntent — no redirect) ✨ ────────
# @app.post("/payments/artwork/intent")
# def create_artwork_intent(artwork_id: str=Form(...), address: str=Form(...), phone: str=Form(...),
#     note: str=Form(""), payment_type: str=Form("online"), current_user=Depends(get_current_user)):
#     try: art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
#     except: raise HTTPException(404, "Artwork not found")
#     if not art: raise HTTPException(404, "Artwork not found")
#     if art["status"] != "listed": raise HTTPException(400, "Artwork not available")
#     order = {"artwork_id": artwork_id, "art_title": art["title"],
#              "art_image_url": art.get("image_url"), "artist_id": art["artist_id"],
#              "artist_name": art["artist_name"], "buyer_id": str(current_user["_id"]),
#              "buyer_name": f"{current_user['first_name']} {current_user['last_name']}",
#              "buyer_email": current_user["email"], "address": address, "phone": phone,
#              "note": note, "amount": float(art["price"]), "payment_type": payment_type,
#              "status": "pending", "created_at": datetime.utcnow().isoformat()}
#     if payment_type == "cod":
#         result = orders_col.insert_one(order)
#         push_notification(art["artist_id"],
#             f"🛒 New COD order for '{art['title']}' from {order['buyer_name']}!")
#         return {"order_id": str(result.inserted_id), "type": "cod"}
#     intent = stripe.PaymentIntent.create(
#         amount=int(float(art["price"]) * 100), currency="inr",
#         description=f"Artwork: {art['title']}", payment_method_types=["card"],
#         metadata={"artwork_id": artwork_id, "user_id": str(current_user["_id"]), "type": "artwork"})
#     order["stripe_pi_id"] = intent.id
#     result = orders_col.insert_one(order)
#     return {"client_secret": intent.client_secret, "order_id": str(result.inserted_id), "type": "online"}

# # @app.post("/payments/artwork/intent/confirm")
# # def confirm_artwork_intent(payment_intent_id: str=Form(...), order_id: str=Form(...),
# #                             current_user=Depends(get_current_user)):
# #     try: intent = stripe.PaymentIntent.retrieve(payment_intent_id)
# #     except stripe.error.StripeError as e: raise HTTPException(400, str(e))
# #     if intent.status != "succeeded": raise HTTPException(400, f"Payment not completed: {intent.status}")
# #     try:
# #         orders_col.update_one({"_id": ObjectId(order_id)},
# #             {"$set": {"status": "approved", "payment_status": "paid", "paid_at": datetime.utcnow().isoformat()}})
# #     except: pass
# #     artwork_id = intent.metadata.get("artwork_id")
# #     try:
# #         art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
# #         if art:
# #             artworks_col.update_one({"_id": ObjectId(artwork_id)}, {"$set": {"status": "sold"}})
# #             push_notification(art["artist_id"],
# #                 f"🎨 {current_user['first_name']} {current_user['last_name']} bought '{art['title']}' — ₹{art['price']} earned!")
# #     except: pass
# #     return {"message": "Payment confirmed", "artwork_id": artwork_id}

# @app.post("/payments/artwork/intent/confirm")
# def confirm_artwork_intent(payment_intent_id: str=Form(...), order_id: str=Form(...),
#                             current_user=Depends(get_current_user)):
#     try: intent = stripe.PaymentIntent.retrieve(payment_intent_id)
#     except stripe.error.StripeError as e: raise HTTPException(400, str(e))
#     if intent.status != "succeeded": raise HTTPException(400, f"Payment not completed: {intent.status}")
#     try:
#         orders_col.update_one({"_id": ObjectId(order_id)},
#             {"$set": {"status": "approved", "payment_status": "paid", "paid_at": datetime.utcnow().isoformat()}})
#     except: pass
#     artwork_id = intent.metadata.get("artwork_id")
#     try:
#         art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
#         if art:
#             artworks_col.update_one({"_id": ObjectId(artwork_id)}, {"$set": {"status": "sold"}})
#             # ✅ payments collection mein record add karo
#             payments_col.insert_one({
#                 "user_id": str(current_user["_id"]),
#                 "buyer_name": f"{current_user['first_name']} {current_user['last_name']}",
#                 "artwork_id": artwork_id,
#                 "art_title": art["title"],
#                 "artist_id": art["artist_id"],
#                 "artist_name": art["artist_name"],
#                 "amount": int(float(art["price"]) * 100),
#                 "amount_inr": float(art["price"]),
#                 "stripe_pi_id": payment_intent_id,
#                 "type": "artwork_sale",
#                 "status": "completed",
#                 "created_at": datetime.utcnow().isoformat(),
#                 "paid_at": datetime.utcnow().isoformat()
#             })
#             push_notification(art["artist_id"],
#                 f"🎨 {current_user['first_name']} {current_user['last_name']} bought '{art['title']}' — ₹{art['price']} earned!")
#     except: pass
#     return {"message": "Payment confirmed", "artwork_id": artwork_id}

# # ── PAYMENTS — TUTORIAL (PaymentIntent — no redirect) ✨ ───────
# @app.post("/payments/tutorial/intent")
# def create_tutorial_intent(tutorial_id: str=Form(...), current_user=Depends(get_current_user)):
#     try: tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
#     except: raise HTTPException(404, "Tutorial not found")
#     if not tut: raise HTTPException(404, "Tutorial not found")
#     if payments_col.find_one({"user_id": str(current_user["_id"]), "tutorial_id": tutorial_id, "status": "completed"}):
#         raise HTTPException(400, "Already purchased")
#     intent = stripe.PaymentIntent.create(
#         amount=int(float(tut["price"]) * 100), currency="inr",
#         description=f"Tutorial: {tut['title']}", payment_method_types=["card"],
#         metadata={"tutorial_id": tutorial_id, "user_id": str(current_user["_id"]), "type": "tutorial"})
#     payments_col.insert_one({"user_id": str(current_user["_id"]), "tutorial_id": tutorial_id,
#                               "type": "tutorial", "amount": float(tut["price"]),
#                               "stripe_pi_id": intent.id, "status": "pending",
#                               "created_at": datetime.utcnow().isoformat()})
#     return {"client_secret": intent.client_secret, "tutorial_id": tutorial_id}

# @app.post("/payments/tutorial/intent/confirm")
# def confirm_tutorial_intent(payment_intent_id: str=Form(...), tutorial_id: str=Form(...),
#                               current_user=Depends(get_current_user)):
#     try: intent = stripe.PaymentIntent.retrieve(payment_intent_id)
#     except stripe.error.StripeError as e: raise HTTPException(400, str(e))
#     if intent.status != "succeeded": raise HTTPException(400, f"Payment not completed: {intent.status}")
#     payments_col.update_one({"stripe_pi_id": payment_intent_id},
#         {"$set": {"status": "completed", "paid_at": datetime.utcnow().isoformat()}})
#     try:
#         tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
#         if tut:
#             tutorials_col.update_one({"_id": ObjectId(tutorial_id)},
#                 {"$inc": {"students": 1, "earnings": float(tut["price"])}})
#             push_notification(tut["artist_id"],
#                 f"🎬 {current_user['first_name']} {current_user['last_name']} purchased '{tut['title']}' — ₹{tut['price']} earned!")
#     except: pass
#     return {"message": "Tutorial unlocked", "tutorial_id": tutorial_id}

# # ── PAYMENTS — ARTWORK (Checkout redirect — legacy) ────────────
# @app.post("/payments/artwork/checkout")
# def create_artwork_checkout(artwork_id: str=Form(...), address: str=Form(...), phone: str=Form(...),
#     note: str=Form(""), payment_type: str=Form("online"), current_user=Depends(get_current_user)):
#     try: art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
#     except: raise HTTPException(404, "Artwork not found")
#     if not art or art["status"] != "listed": raise HTTPException(400, "Artwork not available")
#     order = {"artwork_id": artwork_id, "art_title": art["title"], "art_image_url": art.get("image_url"),
#              "artist_id": art["artist_id"], "artist_name": art["artist_name"],
#              "buyer_id": str(current_user["_id"]),
#              "buyer_name": f"{current_user['first_name']} {current_user['last_name']}",
#              "buyer_email": current_user["email"], "address": address, "phone": phone, "note": note,
#              "amount": float(art["price"]), "payment_type": payment_type,
#              "status": "pending", "created_at": datetime.utcnow().isoformat()}
#     if payment_type == "cod":
#         result = orders_col.insert_one(order)
#         push_notification(art["artist_id"], f"🛒 New COD order for '{art['title']}' from {order['buyer_name']}!")
#         return {"order_id": str(result.inserted_id), "message": "COD order placed"}
#     session = stripe.checkout.Session.create(
#         payment_method_types=["card"],
#         line_items=[{"price_data": {"currency": "inr", "unit_amount": int(float(art["price"]) * 100),
#                                      "product_data": {"name": art["title"]}}, "quantity": 1}],
#         mode="payment",
#         success_url=f"{FRONTEND_URL}/customer.html?session_id={{CHECKOUT_SESSION_ID}}&type=artwork&id={artwork_id}",
#         cancel_url=f"{FRONTEND_URL}/customer.html",
#         metadata={"artwork_id": artwork_id, "user_id": str(current_user["_id"]), "type": "artwork"})
#     order["stripe_session_id"] = session.id
#     result = orders_col.insert_one(order)
#     return {"checkout_url": session.url, "order_id": str(result.inserted_id)}

# @app.post("/payments/artwork/verify")
# def verify_artwork_payment(session_id: str=Form(...), current_user=Depends(get_current_user)):
#     try: session = stripe.checkout.Session.retrieve(session_id)
#     except stripe.error.StripeError as e: raise HTTPException(400, str(e))
#     if session.payment_status != "paid": raise HTTPException(400, "Payment not completed")
#     artwork_id = session.metadata.get("artwork_id")
#     orders_col.update_one({"stripe_session_id": session_id},
#         {"$set": {"status": "approved", "paid_at": datetime.utcnow().isoformat()}})
#     try:
#         artworks_col.update_one({"_id": ObjectId(artwork_id)}, {"$set": {"status": "sold"}})
#         art2 = artworks_col.find_one({"_id": ObjectId(artwork_id)})
#         if art2:
#             push_notification(art2["artist_id"],
#                 f"🎨 {current_user['first_name']} {current_user['last_name']} bought '{art2['title']}' — ₹{art2['price']} earned!")
#     except: pass
#     return {"message": "Payment verified", "artwork_id": artwork_id}

# # ── PAYMENTS — TUTORIAL (Checkout redirect — legacy) ──────────
# @app.post("/payments/tutorial/checkout")
# def create_tutorial_checkout(tutorial_id: str=Form(...), current_user=Depends(get_current_user)):
#     try: tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
#     except: raise HTTPException(404, "Tutorial not found")
#     if not tut: raise HTTPException(404, "Tutorial not found")
#     if payments_col.find_one({"user_id": str(current_user["_id"]), "tutorial_id": tutorial_id, "status": "completed"}):
#         raise HTTPException(400, "Already purchased")
#     session = stripe.checkout.Session.create(
#         payment_method_types=["card"],
#         line_items=[{"price_data": {"currency": "inr", "unit_amount": int(float(tut["price"]) * 100),
#                                      "product_data": {"name": tut["title"], "description": f"Tutorial by {tut['artist_name']}"}},
#                      "quantity": 1}],
#         mode="payment",
#         success_url=f"{FRONTEND_URL}/customer.html?session_id={{CHECKOUT_SESSION_ID}}&type=tutorial&id={tutorial_id}",
#         cancel_url=f"{FRONTEND_URL}/customer.html",
#         metadata={"tutorial_id": tutorial_id, "user_id": str(current_user["_id"]), "type": "tutorial"})
#     payments_col.insert_one({"user_id": str(current_user["_id"]), "tutorial_id": tutorial_id,
#                               "type": "tutorial", "amount": float(tut["price"]),
#                               "stripe_session_id": session.id, "status": "pending",
#                               "created_at": datetime.utcnow().isoformat()})
#     return {"checkout_url": session.url, "session_id": session.id}

# @app.post("/payments/tutorial/verify")
# def verify_tutorial_payment(session_id: str=Form(...), current_user=Depends(get_current_user)):
#     try: session = stripe.checkout.Session.retrieve(session_id)
#     except stripe.error.StripeError as e: raise HTTPException(400, str(e))
#     if session.payment_status != "paid": raise HTTPException(400, "Payment not completed")
#     tutorial_id = session.metadata.get("tutorial_id")
#     payments_col.update_one({"stripe_session_id": session_id},
#         {"$set": {"status": "completed", "paid_at": datetime.utcnow().isoformat()}})
#     try:
#         tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
#         if tut:
#             tutorials_col.update_one({"_id": ObjectId(tutorial_id)},
#                 {"$inc": {"students": 1, "earnings": float(tut["price"])}})
#             push_notification(tut["artist_id"],
#                 f"🎬 {current_user['first_name']} {current_user['last_name']} purchased '{tut['title']}' — ₹{tut['price']} earned!")
#     except: pass
#     return {"message": "Payment verified", "tutorial_id": tutorial_id}

# # ── STRIPE WEBHOOK ────────────────────────────────────────────
# @app.post("/webhook/stripe")
# async def stripe_webhook(request: Request):
#     payload = await request.body()
#     webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
#     if webhook_secret:
#         try: event = stripe.Webhook.construct_event(payload, request.headers.get("stripe-signature", ""), webhook_secret)
#         except: raise HTTPException(400, "Invalid signature")
#     else:
#         import json; event = json.loads(payload)
#     if event["type"] == "checkout.session.completed":
#         session = event["data"]["object"]; meta = session.get("metadata", {})
#         pt = meta.get("type")
#         if pt == "tutorial":
#             tid = meta.get("tutorial_id")
#             payments_col.update_one({"stripe_session_id": session["id"]},
#                 {"$set": {"status": "completed", "paid_at": datetime.utcnow().isoformat()}})
#             try:
#                 tut = tutorials_col.find_one({"_id": ObjectId(tid)})
#                 if tut:
#                     tutorials_col.update_one({"_id": ObjectId(tid)},
#                         {"$inc": {"students": 1, "earnings": float(tut["price"])}})
#                     push_notification(tut["artist_id"], f"🎬 Someone purchased '{tut['title']}' — ₹{tut['price']} earned!")
#             except: pass
#         elif pt == "artwork":
#             aid = meta.get("artwork_id")
#             orders_col.update_one({"stripe_session_id": session["id"]},
#                 {"$set": {"status": "approved", "paid_at": datetime.utcnow().isoformat()}})
#             try:
#                 art2 = artworks_col.find_one({"_id": ObjectId(aid)})
#                 if art2:
#                     artworks_col.update_one({"_id": ObjectId(aid)}, {"$set": {"status": "sold"}})
#                     push_notification(art2["artist_id"], f"🎨 '{art2['title']}' sold! — ₹{art2['price']} earned!")
#             except: pass
#     return {"received": True}

# # ── ORDERS ────────────────────────────────────────────────────
# @app.get("/orders/mine")
# def my_orders_as_buyer(current_user=Depends(get_current_user)):
#     return [to_str_id(o) for o in orders_col.find({"buyer_id": str(current_user["_id"])}).sort("created_at", -1)]

# @app.get("/orders/artist")
# def my_orders_as_artist(current_user=Depends(get_current_user)):
#     if current_user["role"] != "artist": raise HTTPException(403, "Artists only")
#     return [to_str_id(o) for o in orders_col.find({"artist_id": str(current_user["_id"])}).sort("created_at", -1)]

# @app.put("/orders/{order_id}/status")
# def update_order_status(order_id: str, status: str=Form(...), current_user=Depends(get_current_user)):
#     try: order = orders_col.find_one({"_id": ObjectId(order_id)})
#     except: raise HTTPException(404, "Not found")
#     if not order: raise HTTPException(404, "Order not found")
#     if current_user["role"] == "artist" and order["artist_id"] != str(current_user["_id"]): raise HTTPException(403, "Not your order")
#     if current_user["role"] == "customer" and order["buyer_id"] != str(current_user["_id"]): raise HTTPException(403, "Not your order")
#     orders_col.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": status}})
#     msgs = {"approved": (order["buyer_id"], f"✅ Your order for '{order['art_title']}' was approved!"),
#             "rejected": (order["buyer_id"], f"❌ Your order for '{order['art_title']}' was rejected."),
#             "shipped":  (order["buyer_id"], f"📦 Your order '{order['art_title']}' has been shipped!"),
#             "delivered":(order["artist_id"],f"🎉 Order '{order['art_title']}' marked as delivered.")}
#     if status in msgs: push_notification(*msgs[status])
#     return {"message": f"Order {status}"}

# # ── JOBS ──────────────────────────────────────────────────────
# @app.post("/jobs")
# def create_job(title: str=Form(...), budget: str=Form(...), job_type: str=Form("Freelance"),
#     location: str=Form("Remote"), dept: str=Form(""), deadline: str=Form(""),
#     skills: str=Form(""), desc: str=Form(""), status: str=Form("active"),
#     current_user=Depends(get_current_user)):
#     if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
#     job = {"brand_id": str(current_user["_id"]),
#            "brand_name": current_user.get("brand_name") or f"{current_user['first_name']} {current_user['last_name']}",
#            "title": title, "budget": budget, "job_type": job_type, "location": location,
#            "dept": dept, "deadline": deadline,
#            "skills": [s.strip() for s in skills.split(",") if s.strip()],
#            "desc": desc, "status": status, "created_at": datetime.utcnow().isoformat()}
#     result = jobs_col.insert_one(job); job["_id"] = str(result.inserted_id)
#     return job

# @app.get("/jobs")
# def list_jobs(status: Optional[str]="active"):
#     query = {"status": status} if status else {}
#     return [to_str_id(j) for j in jobs_col.find(query).sort("created_at", -1)]

# @app.put("/jobs/{job_id}")
# def update_job(job_id: str, title: Optional[str]=Form(None), budget: Optional[str]=Form(None),
#     job_type: Optional[str]=Form(None), location: Optional[str]=Form(None),
#     skills: Optional[str]=Form(None), desc: Optional[str]=Form(None),
#     current_user=Depends(get_current_user)):
#     if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
#     update = {k: v for k, v in {"title": title, "budget": budget, "job_type": job_type,
#                                   "location": location, "desc": desc}.items() if v is not None}
#     if skills is not None: update["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
#     if update: jobs_col.update_one({"_id": ObjectId(job_id)}, {"$set": update})
#     return to_str_id(jobs_col.find_one({"_id": ObjectId(job_id)}))

# @app.delete("/jobs/{job_id}")
# def delete_job(job_id: str, current_user=Depends(get_current_user)):
#     if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
#     jobs_col.delete_one({"_id": ObjectId(job_id)})
#     db["applications"].delete_many({"job_id": job_id})
#     return {"message": "Deleted"}

# @app.post("/jobs/{job_id}/apply")
# def apply_to_job(job_id: str, message: str=Form(""), current_user=Depends(get_current_user)):
#     if current_user["role"] != "artist": raise HTTPException(403, "Artists only")
#     try: job = jobs_col.find_one({"_id": ObjectId(job_id)})
#     except: raise HTTPException(404, "Job not found")
#     if not job: raise HTTPException(404, "Job not found")
#     if db["applications"].find_one({"job_id": job_id, "artist_id": str(current_user["_id"])}):
#         raise HTTPException(400, "Already applied")
#     app_doc = {"job_id": job_id, "job_title": job["title"], "brand_id": job["brand_id"],
#                "artist_id": str(current_user["_id"]),
#                "artist_name": f"{current_user['first_name']} {current_user['last_name']}",
#                "artist_avatar": current_user.get("avatar_url"),
#                "skills": current_user.get("skills", []), "city": current_user.get("city", ""),
#                "medium": current_user.get("medium", ""), "message": message,
#                "status": "pending", "applied_at": datetime.utcnow().isoformat()}
#     db["applications"].insert_one(app_doc)
#     push_notification(job["brand_id"], f"🎨 New application from {app_doc['artist_name']} for '{job['title']}'")
#     return {"message": "Application sent"}

# @app.get("/jobs/applications")
# def get_applications(current_user=Depends(get_current_user)):
#     uid = str(current_user["_id"])
#     query = {"brand_id": uid} if current_user["role"] == "brand" else {"artist_id": uid}
#     return [to_str_id(a) for a in db["applications"].find(query).sort("applied_at", -1)]

# @app.get("/jobs/{job_id}/applications")
# def get_job_applications(job_id: str, current_user=Depends(get_current_user)):
#     if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
#     return [to_str_id(a) for a in db["applications"].find({"job_id": job_id})]

# @app.put("/jobs/applications/{app_id}/status")
# def update_application_status(app_id: str, status: str=Form(...), current_user=Depends(get_current_user)):
#     if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
#     try: db["applications"].update_one({"_id": ObjectId(app_id)}, {"$set": {"status": status}})
#     except: raise HTTPException(404, "Application not found")
#     return {"message": f"Status updated to {status}"}

# # ── COMPETITIONS ──────────────────────────────────────────────
# @app.post("/competitions")
# def create_competition(title: str=Form(...), prize: str=Form(...), category: str=Form("Other"),
#     start_date: str=Form(""), end_date: str=Form(""), desc: str=Form(""), tags: str=Form(""),
#     current_user=Depends(get_current_user)):
#     if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
#     comp = {"brand_id": str(current_user["_id"]),
#             "brand_name": current_user.get("brand_name") or f"{current_user['first_name']} {current_user['last_name']}",
#             "title": title, "prize": prize, "category": category, "start_date": start_date,
#             "end_date": end_date, "desc": desc,
#             "tags": [t.strip() for t in tags.split(",") if t.strip()],
#             "entries": 0, "status": "active", "created_at": datetime.utcnow().isoformat()}
#     result = db["competitions"].insert_one(comp); comp["_id"] = str(result.inserted_id)
#     return comp

# @app.get("/competitions")
# def list_competitions(status: Optional[str]="active", brand_id: Optional[str]=None):
#     query = {}
#     if status: query["status"] = status
#     if brand_id: query["brand_id"] = brand_id
#     return [to_str_id(c) for c in db["competitions"].find(query).sort("created_at", -1)]

# @app.get("/competitions/mine/registered")
# def my_registered_competitions(current_user=Depends(get_current_user)):
#     return [{"comp_id": r["comp_id"]} for r in db["comp_registrations"].find({"artist_id": str(current_user["_id"])})]

# @app.get("/competitions/{comp_id}/registrations")
# def get_competition_registrations(comp_id: str, current_user=Depends(get_current_user)):
#     return [{"artist_id": r.get("artist_id"), "artist_name": r.get("artist_name"),
#              "registered_at": r.get("registered_at")} for r in db["comp_registrations"].find({"comp_id": comp_id})]

# @app.post("/competitions/{comp_id}/register")
# def register_competition(comp_id: str, current_user=Depends(get_current_user)):
#     if current_user["role"] != "artist": raise HTTPException(403, "Artists only")
#     if db["comp_registrations"].find_one({"comp_id": comp_id, "artist_id": str(current_user["_id"])}):
#         raise HTTPException(400, "Already registered")
#     db["comp_registrations"].insert_one({"comp_id": comp_id, "artist_id": str(current_user["_id"]),
#         "artist_name": f"{current_user['first_name']} {current_user['last_name']}",
#         "registered_at": datetime.utcnow().isoformat()})
#     try:
#         db["competitions"].update_one({"_id": ObjectId(comp_id)}, {"$inc": {"entries": 1}})
#         comp_doc = db["competitions"].find_one({"_id": ObjectId(comp_id)})
#         if comp_doc: push_notification(comp_doc["brand_id"],
#             f"🏆 {current_user['first_name']} {current_user['last_name']} registered for '{comp_doc['title']}'")
#     except: pass
#     return {"message": "Registered"}

# # ── MESSAGES ─────────────────────────────────────────────────
# @app.post("/messages/send")
# def send_message(recipient_id: str=Form(...), body: str=Form(...), current_user=Depends(get_current_user)):
#     sender_id = str(current_user["_id"])
#     thread_id = "_".join(sorted([sender_id, recipient_id]))
#     messages_col.insert_one({"thread_id": thread_id, "from_id": sender_id, "to_id": recipient_id,
#         "from_name": f"{current_user['first_name']} {current_user['last_name']}",
#         "body": body, "read": False, "created_at": datetime.utcnow().isoformat()})
#     return {"message": "Sent", "thread_id": thread_id}

# @app.get("/messages/threads")
# def my_threads(current_user=Depends(get_current_user)):
#     user_id = str(current_user["_id"])
#     msgs    = list(messages_col.find({"$or": [{"from_id": user_id}, {"to_id": user_id}]}).sort("created_at", -1))
#     threads = {}
#     for m in msgs:
#         tid = m["thread_id"]
#         if tid not in threads:
#             other_id = m["to_id"] if m["from_id"] == user_id else m["from_id"]
#             other    = users_col.find_one({"_id": ObjectId(other_id)}) if other_id else None
#             threads[tid] = {"thread_id": tid,
#                 "other_user": {"id": other_id,
#                                "name": f"{other['first_name']} {other['last_name']}" if other else "Unknown",
#                                "avatar_url": other.get("avatar_url") if other else None,
#                                "role": other.get("role") if other else ""} if other else {},
#                 "last_message": to_str_id(m), "unread_count": 0}
#         if m["to_id"] == user_id and not m["read"]: threads[tid]["unread_count"] += 1
#     return list(threads.values())

# @app.get("/messages/thread/{thread_id}")
# def get_thread(thread_id: str, current_user=Depends(get_current_user)):
#     user_id = str(current_user["_id"])
#     if user_id not in thread_id.split("_"): raise HTTPException(403, "Not your thread")
#     msgs = [to_str_id(m) for m in messages_col.find({"thread_id": thread_id}).sort("created_at", 1)]
#     messages_col.update_many({"thread_id": thread_id, "to_id": user_id, "read": False}, {"$set": {"read": True}})
#     return msgs

# # ── NOTIFICATIONS ─────────────────────────────────────────────
# @app.get("/notifications")
# def get_notifications(current_user=Depends(get_current_user)):
#     return [to_str_id(n) for n in notifs_col.find({"user_id": str(current_user["_id"])}).sort("created_at", -1).limit(50)]

# @app.put("/notifications/read-all")
# def mark_all_notifications_read(current_user=Depends(get_current_user)):
#     notifs_col.update_many({"user_id": str(current_user["_id"]), "read": False}, {"$set": {"read": True}})
#     return {"message": "All marked as read"}

# # ── ARTISTS ───────────────────────────────────────────────────
# @app.get("/artists")
# def search_artists(search: Optional[str]=None, medium: Optional[str]=None, city: Optional[str]=None):
#     query: dict = {"role": "artist"}
#     if medium: query["medium"] = {"$regex": medium, "$options": "i"}
#     if city:   query["city"]   = {"$regex": city,   "$options": "i"}
#     if search:
#         query["$or"] = [{"first_name": {"$regex": search, "$options": "i"}},
#                         {"last_name":  {"$regex": search, "$options": "i"}},
#                         {"medium":     {"$regex": search, "$options": "i"}},
#                         {"city":       {"$regex": search, "$options": "i"}},
#                         {"skills":     {"$in": [search]}}]
#     artists = []
#     for u in users_col.find(query):
#         u = to_str_id(u); u.pop("password_hash", None); u.pop("session_token", None)
#         u["listed_artworks"] = artworks_col.count_documents({"artist_id": u["_id"], "status": "listed"})
#         artists.append(u)
#     return artists

# @app.get("/artists/{artist_id}")
# def get_artist_profile(artist_id: str):
#     try: user = users_col.find_one({"_id": ObjectId(artist_id), "role": "artist"})
#     except: raise HTTPException(404, "Not found")
#     if not user: raise HTTPException(404, "Artist not found")
#     user = to_str_id(user); user.pop("password_hash", None); user.pop("session_token", None)
#     user["artworks"] = [to_str_id(a) for a in artworks_col.find({"artist_id": artist_id, "status": "listed"})]
#     tuts = []
#     for t in tutorials_col.find({"artist_id": artist_id}):
#         t = to_str_id(t); t.pop("video_url", None); tuts.append(t)
#     user["tutorials"] = tuts
#     return user

# # ── BRAND PAYMENTS ────────────────────────────────────────────
# @app.post("/payments/brand/pay-artist")
# def brand_pay_artist(artist_id: str=Form(...), amount: float=Form(...),
#     desc: str=Form("Job Payment"), notes: str=Form(""), current_user=Depends(get_current_user)):
#     if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
#     try: artist = users_col.find_one({"_id": ObjectId(artist_id), "role": "artist"})
#     except: raise HTTPException(404, "Artist not found")
#     if not artist: raise HTTPException(404, "Artist not found")
#     artist_name = f"{artist['first_name']} {artist['last_name']}"
#     brand_name  = current_user.get("brand_name") or f"{current_user['first_name']} {current_user['last_name']}"
#     amount_paise = int(float(amount))
#     intent = stripe.PaymentIntent.create(amount=amount_paise, currency="inr",
#         description=f"{desc} — {artist_name} (ArtCraft)", payment_method_types=["card"],
#         metadata={"brand_id": str(current_user["_id"]), "artist_id": artist_id,
#                   "artist_name": artist_name, "desc": desc, "type": "brand_payment"})
#     payments_col.insert_one({"brand_id": str(current_user["_id"]), "brand_name": brand_name,
#         "artist_id": artist_id, "artist_name": artist_name, "amount": amount_paise,
#         "desc": desc, "notes": notes, "stripe_pi_id": intent.id, "client_secret": intent.client_secret,
#         "type": "brand_payment", "status": "pending", "created_at": datetime.utcnow().isoformat()})
#     return {"client_secret": intent.client_secret, "payment_intent_id": intent.id,
#             "amount_paise": amount_paise, "artist_name": artist_name}

# @app.post("/payments/brand/confirm")
# def confirm_brand_payment(payment_intent_id: str=Form(...), current_user=Depends(get_current_user)):
#     if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
#     try: intent = stripe.PaymentIntent.retrieve(payment_intent_id)
#     except stripe.error.StripeError as e: raise HTTPException(400, str(e))
#     if intent.status != "succeeded": raise HTTPException(400, f"Payment not succeeded: {intent.status}")
#     pay_record = payments_col.find_one_and_update({"stripe_pi_id": payment_intent_id},
#         {"$set": {"status": "completed", "paid_at": datetime.utcnow().isoformat()}})
#     if pay_record:
#         amount_inr = int(pay_record.get("amount", 0)) // 100
#         push_notification(pay_record["artist_id"],
#             f"💰 {pay_record['brand_name']} sent you ₹{amount_inr:,} — '{pay_record['desc']}'")
#     return {"message": "Payment confirmed"}

# @app.get("/payments/brand/history")
# def brand_payment_history(current_user=Depends(get_current_user)):
#     if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
#     pays = []
#     for p in payments_col.find({"brand_id": str(current_user["_id"]), "type": "brand_payment"}).sort("created_at", -1):
#         p = to_str_id(p)
#         raw = p.get("amount", 0)
#         p["amount_inr"] = int(raw) // 100 if raw > 1000 else int(raw)
#         pays.append(p)
#     return pays

# @app.get("/payments/artist/received")
# def artist_received_payments(current_user=Depends(get_current_user)):
#     return [to_str_id(p) for p in payments_col.find(
#         {"artist_id": str(current_user["_id"]), "type": "brand_payment", "status": "completed"}).sort("paid_at", -1)]

# # ── AI CHAT ───────────────────────────────────────────────────
# class AIChatRequest(BaseModel):
#     messages: List[dict]

# @app.post("/ai/chat")
# async def ai_chat(body: AIChatRequest, current_user=Depends(get_current_user)):
#     if not GROQ_API_KEY: raise HTTPException(500, "AI service not configured — add GROQ_API_KEY to .env")
#     groq_messages = [{"role": "system", "content": ARTCRAFT_AI_SYSTEM}] + body.messages
#     try:
#         async with httpx.AsyncClient(timeout=30) as c:
#             resp = await c.post(GROQ_CHAT_URL,
#                 headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
#                 json={"model": GROQ_MODEL, "messages": groq_messages, "max_tokens": 300, "temperature": 0.7})
#         resp.raise_for_status()
#         return {"reply": resp.json()["choices"][0]["message"]["content"]}
#     except httpx.HTTPStatusError as e: raise HTTPException(502, f"Groq API error: {e.response.text[:200]}")
#     except Exception as e: raise HTTPException(502, f"AI service unavailable: {str(e)}")


# @app.get("/config/stripe")
# def get_stripe_config():
#     pk = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_51TFUEsAkOvpUa6hU6G5cJIq9DFNZ7rEpwzVGxgFIjg0Kxzdqz6qtyOAW5ehNkGwrQa5CEUHnMBEUP5J7b2s3cHOG00Rgban7QN")
#     if not pk:
#         raise HTTPException(500, "Stripe publishable key not configured")
#     return {"publishable_key": pk}

# # ── HEALTH ────────────────────────────────────────────────────
# @app.get("/")
# def root(): return {"app": "ArtCraft API", "version": "1.0.0", "status": "running", "docs": "/docs"}

# @app.get("/health")
# def health():
#     try: client.admin.command("ping"); db_ok = True
#     except: db_ok = False
#     return {"api": "ok", "mongodb": "ok" if db_ok else "error"}

"""
ArtCraft Backend — FastAPI + MongoDB (PyMongo) + Stripe + Groq AI
"""
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import hashlib, uuid, os, stripe, httpx
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ArtCraft API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client    = MongoClient(MONGO_URL)
db        = client["artcraft"]

users_col     = db["users"]
artworks_col  = db["artworks"]
tutorials_col = db["tutorials"]
orders_col    = db["orders"]
payments_col  = db["payments"]
jobs_col      = db["jobs"]
messages_col  = db["messages"]
notifs_col    = db["notifications"]

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
# FRONTEND_URL   = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
GROQ_CHAT_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "llama-3.1-8b-instant"
ARTCRAFT_AI_SYSTEM = ("You are ArtCraft AI, a helpful assistant for Indian artists. "
    "Help with artwork pricing, writing bios, getting more buyers, marketing on social media, "
    "creating tutorials, dealing with brand collaborations, and running an art business in India. "
    "Be concise, friendly, practical. Keep responses under 150 words. Use simple English.")

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def make_token(uid):  return hashlib.sha256(f"{uid}{uuid.uuid4()}".encode()).hexdigest()
def to_str_id(doc):
    if doc and "_id" in doc: doc["_id"] = str(doc["_id"])
    return doc

# ── STRIPE HELPER — works with both old & new stripe SDK ──────
def get_metadata(stripe_obj, key, default=None):
    try:
        meta = stripe_obj["metadata"]
        if meta is None: return default
        return meta.get(key, default) if hasattr(meta, "get") else meta[key]
    except Exception:
        return default

def get_intent_field(stripe_obj, field):
    try:
        return stripe_obj[field]
    except Exception:
        return getattr(stripe_obj, field, None)

def get_current_user(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "): raise HTTPException(401, "Not authenticated")
    user = users_col.find_one({"session_token": auth[7:]})
    if not user: raise HTTPException(401, "Invalid or expired token")
    return user

def save_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    fp  = os.path.join("uploads", f"{uuid.uuid4()}{ext}")
    with open(fp, "wb") as f: f.write(file.file.read())
    return fp

def push_notification(user_id: str, text: str):
    notifs_col.insert_one({"user_id": user_id, "text": text, "read": False,
                            "created_at": datetime.utcnow().isoformat()})

# ── AUTH ──────────────────────────────────────────────────────
@app.post("/auth/signup")
def signup(first_name: str=Form(...), last_name: str=Form(...), email: str=Form(...),
           password: str=Form(...), role: str=Form(...)):
    email = email.lower().strip()
    if users_col.find_one({"email": email, "role": role}):
        raise HTTPException(400, "Account already exists for this email + role")
    user = {"first_name": first_name, "last_name": last_name, "email": email,
            "password_hash": hash_password(password), "role": role, "session_token": None,
            "avatar_url": None, "cover_url": None, "created_at": datetime.utcnow().isoformat(),
            "medium": "", "city": "", "bio": "", "skills": [], "instagram": "", "website": "",
            "brand_name": "", "industry": "", "stripe_key": "", "upi": "", "bank_account": "", "ifsc": ""}
    result = users_col.insert_one(user)
    token  = make_token(str(result.inserted_id))
    users_col.update_one({"_id": result.inserted_id}, {"$set": {"session_token": token}})
    return {"token": token, "user_id": str(result.inserted_id), "role": role,
            "name": f"{first_name} {last_name}", "email": email}

@app.post("/auth/login")
def login(email: str=Form(...), password: str=Form(...), role: str=Form(...)):
    email = email.lower().strip()
    user  = users_col.find_one({"email": email, "role": role})
    if not user or user["password_hash"] != hash_password(password):
        raise HTTPException(401, "Incorrect email, password, or role")
    token = make_token(str(user["_id"]))
    users_col.update_one({"_id": user["_id"]}, {"$set": {"session_token": token}})
    return {"token": token, "user_id": str(user["_id"]), "role": user["role"],
            "name": f"{user['first_name']} {user['last_name']}", "email": user["email"]}

@app.post("/auth/logout")
def logout(current_user=Depends(get_current_user)):
    users_col.update_one({"_id": current_user["_id"]}, {"$set": {"session_token": None}})
    return {"message": "Logged out"}

@app.get("/auth/me")
def get_me(current_user=Depends(get_current_user)):
    return to_str_id({**current_user, "password_hash": "[hidden]"})

# ── PROFILE ───────────────────────────────────────────────────
@app.put("/profile")
def update_profile(first_name: Optional[str]=Form(None), last_name: Optional[str]=Form(None),
    medium: Optional[str]=Form(None), city: Optional[str]=Form(None), bio: Optional[str]=Form(None),
    instagram: Optional[str]=Form(None), website: Optional[str]=Form(None),
    brand_name: Optional[str]=Form(None), industry: Optional[str]=Form(None),
    phone: Optional[str]=Form(None), upi: Optional[str]=Form(None),
    bank_account: Optional[str]=Form(None), ifsc: Optional[str]=Form(None),
    avatar: Optional[UploadFile]=File(None), cover: Optional[UploadFile]=File(None),
    current_user=Depends(get_current_user)):
    update = {}
    for k, v in {"first_name": first_name, "last_name": last_name, "medium": medium,
                  "city": city, "bio": bio, "instagram": instagram, "website": website,
                  "brand_name": brand_name, "industry": industry, "phone": phone,
                  "upi": upi, "bank_account": bank_account, "ifsc": ifsc}.items():
        if v is not None: update[k] = v
    if avatar: update["avatar_url"] = "/" + save_upload(avatar)
    if cover:  update["cover_url"]  = "/" + save_upload(cover)
    if update: users_col.update_one({"_id": current_user["_id"]}, {"$set": update})
    return to_str_id({**users_col.find_one({"_id": current_user["_id"]}), "password_hash": "[hidden]"})

@app.post("/profile/skills")
def add_skill(skill: str=Form(...), current_user=Depends(get_current_user)):
    users_col.update_one({"_id": current_user["_id"]}, {"$addToSet": {"skills": skill}})
    return {"message": "Skill added"}

@app.delete("/profile/skills/{skill}")
def remove_skill(skill: str, current_user=Depends(get_current_user)):
    users_col.update_one({"_id": current_user["_id"]}, {"$pull": {"skills": skill}})
    return {"message": "Skill removed"}

# ── ARTWORKS ──────────────────────────────────────────────────
@app.post("/artworks")
def create_artwork(title: str=Form(...), price: float=Form(...), medium: str=Form("Other"),
    dims: str=Form(""), desc: str=Form(""), status: str=Form("draft"),
    image: Optional[UploadFile]=File(None), current_user=Depends(get_current_user)):
    if current_user["role"] != "artist": raise HTTPException(403, "Only artists can upload artworks")
    image_url = ("/" + save_upload(image)) if image else None
    artwork = {"artist_id": str(current_user["_id"]),
               "artist_name": f"{current_user['first_name']} {current_user['last_name']}",
               "artist_avatar": current_user.get("avatar_url"), "title": title, "price": price,
               "medium": medium, "dims": dims, "desc": desc, "status": status,
               "image_url": image_url, "created_at": datetime.utcnow().isoformat()}
    result = artworks_col.insert_one(artwork)
    artwork["_id"] = str(result.inserted_id)
    return artwork

@app.get("/artworks")
def list_artworks(status: Optional[str]=None, medium: Optional[str]=None,
                  artist_id: Optional[str]=None, search: Optional[str]=None):
    query = {"status": status or "listed"}
    if medium:    query["medium"]    = medium
    if artist_id: query["artist_id"] = artist_id
    if search:
        query["$or"] = [{"title": {"$regex": search, "$options": "i"}},
                        {"artist_name": {"$regex": search, "$options": "i"}},
                        {"medium": {"$regex": search, "$options": "i"}}]
    return [to_str_id(a) for a in artworks_col.find(query).sort("created_at", -1)]

@app.get("/artworks/mine")
def my_artworks(current_user=Depends(get_current_user)):
    return [to_str_id(a) for a in artworks_col.find({"artist_id": str(current_user["_id"])}).sort("created_at", -1)]

@app.get("/artworks/{artwork_id}")
def get_artwork(artwork_id: str):
    try: art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
    except: raise HTTPException(404, "Artwork not found")
    if not art: raise HTTPException(404, "Artwork not found")
    return to_str_id(art)

@app.put("/artworks/{artwork_id}")
def update_artwork(artwork_id: str, title: Optional[str]=Form(None), price: Optional[float]=Form(None),
    medium: Optional[str]=Form(None), dims: Optional[str]=Form(None), desc: Optional[str]=Form(None),
    status: Optional[str]=Form(None), image: Optional[UploadFile]=File(None),
    current_user=Depends(get_current_user)):
    try: art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
    except: raise HTTPException(404, "Not found")
    if not art or art["artist_id"] != str(current_user["_id"]): raise HTTPException(403, "Not your artwork")
    update = {k: v for k, v in {"title": title, "price": price, "medium": medium,
                                  "dims": dims, "desc": desc, "status": status}.items() if v is not None}
    if image: update["image_url"] = "/" + save_upload(image)
    if update: artworks_col.update_one({"_id": ObjectId(artwork_id)}, {"$set": update})
    return to_str_id(artworks_col.find_one({"_id": ObjectId(artwork_id)}))

@app.delete("/artworks/{artwork_id}")
def delete_artwork(artwork_id: str, current_user=Depends(get_current_user)):
    try: art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
    except: raise HTTPException(404, "Not found")
    if not art or art["artist_id"] != str(current_user["_id"]): raise HTTPException(403, "Not your artwork")
    artworks_col.delete_one({"_id": ObjectId(artwork_id)})
    return {"message": "Deleted"}

# ── TUTORIALS ─────────────────────────────────────────────────
@app.post("/tutorials")
def create_tutorial(title: str=Form(...), price: float=Form(...), duration: str=Form(""),
    level: str=Form("Beginner"), lang: str=Form("English"), desc: str=Form(""),
    video: Optional[UploadFile]=File(None), thumb: Optional[UploadFile]=File(None),
    current_user=Depends(get_current_user)):
    if current_user["role"] != "artist": raise HTTPException(403, "Only artists can create tutorials")
    tutorial = {"artist_id": str(current_user["_id"]),
                "artist_name": f"{current_user['first_name']} {current_user['last_name']}",
                "artist_avatar": current_user.get("avatar_url"), "title": title, "price": price,
                "duration": duration, "level": level, "lang": lang, "desc": desc,
                "video_url": ("/" + save_upload(video)) if video else None,
                "thumb_url": ("/" + save_upload(thumb)) if thumb else None,
                "students": 0, "earnings": 0.0, "created_at": datetime.utcnow().isoformat()}
    result = tutorials_col.insert_one(tutorial)
    tutorial["_id"] = str(result.inserted_id)
    return tutorial

@app.get("/tutorials")
def list_tutorials(artist_id: Optional[str]=None):
    query = {"artist_id": artist_id} if artist_id else {}
    tuts = []
    for t in tutorials_col.find(query).sort("created_at", -1):
        t = to_str_id(t); t.pop("video_url", None); tuts.append(t)
    return tuts

@app.get("/tutorials/mine/purchased")
def my_purchased_tutorials(current_user=Depends(get_current_user)):
    paid = payments_col.find({"user_id": str(current_user["_id"]), "status": "completed", "type": "tutorial"})
    tuts = []
    for p in paid:
        try:
            tut = tutorials_col.find_one({"_id": ObjectId(p["tutorial_id"])})
            if tut: tuts.append(to_str_id(tut))
        except: pass
    return tuts

@app.get("/tutorials/{tutorial_id}")
def get_tutorial(tutorial_id: str, request: Request):
    try: tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
    except: raise HTTPException(404, "Not found")
    if not tut: raise HTTPException(404, "Not found")
    tut = to_str_id(tut)
    auth = request.headers.get("Authorization", "")
    current_user = users_col.find_one({"session_token": auth[7:]}) if auth.startswith("Bearer ") else None
    user_id  = str(current_user["_id"]) if current_user else None
    is_owner = user_id and user_id == tut["artist_id"]
    has_bought = bool(payments_col.find_one({"user_id": user_id, "tutorial_id": tutorial_id,
                                              "status": "completed"})) if user_id else False
    if not is_owner and not has_bought:
        tut.pop("video_url", None); tut["locked"] = True
    else:
        tut["locked"] = False
    return tut

@app.delete("/tutorials/{tutorial_id}")
def delete_tutorial(tutorial_id: str, current_user=Depends(get_current_user)):
    try: tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
    except: raise HTTPException(404, "Not found")
    if not tut or tut["artist_id"] != str(current_user["_id"]): raise HTTPException(403, "Not your tutorial")
    tutorials_col.delete_one({"_id": ObjectId(tutorial_id)})
    return {"message": "Deleted"}

# ── PAYMENTS — ARTWORK (PaymentIntent — no redirect) ✨ ────────
@app.post("/payments/artwork/intent")
def create_artwork_intent(artwork_id: str=Form(...), address: str=Form(...), phone: str=Form(...),
    note: str=Form(""), payment_type: str=Form("online"), current_user=Depends(get_current_user)):
    try: art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
    except: raise HTTPException(404, "Artwork not found")
    if not art: raise HTTPException(404, "Artwork not found")
    if art["status"] != "listed": raise HTTPException(400, "Artwork not available")
    order = {"artwork_id": artwork_id, "art_title": art["title"],
             "art_image_url": art.get("image_url"), "artist_id": art["artist_id"],
             "artist_name": art["artist_name"], "buyer_id": str(current_user["_id"]),
             "buyer_name": f"{current_user['first_name']} {current_user['last_name']}",
             "buyer_email": current_user["email"], "address": address, "phone": phone,
             "note": note, "amount": float(art["price"]), "payment_type": payment_type,
             "status": "pending", "created_at": datetime.utcnow().isoformat()}
    if payment_type == "cod":
        result = orders_col.insert_one(order)
        push_notification(art["artist_id"],
            f"🛒 New COD order for '{art['title']}' from {order['buyer_name']}!")
        return {"order_id": str(result.inserted_id), "type": "cod"}
    intent = stripe.PaymentIntent.create(
        amount=int(float(art["price"]) * 100), currency="inr",
        description=f"Artwork: {art['title']}", payment_method_types=["card"],
        metadata={"artwork_id": artwork_id, "user_id": str(current_user["_id"]), "type": "artwork"})
    order["stripe_pi_id"] = get_intent_field(intent, "id")
    result = orders_col.insert_one(order)
    return {"client_secret": get_intent_field(intent, "client_secret"),
            "order_id": str(result.inserted_id), "type": "online"}

@app.post("/payments/artwork/intent/confirm")
def confirm_artwork_intent(payment_intent_id: str=Form(...), order_id: str=Form(...),
                            current_user=Depends(get_current_user)):
    try: intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e: raise HTTPException(400, str(e))
    if get_intent_field(intent, "status") != "succeeded":
        raise HTTPException(400, f"Payment not completed: {get_intent_field(intent, 'status')}")
    try:
        orders_col.update_one({"_id": ObjectId(order_id)},
            {"$set": {"status": "approved", "payment_status": "paid", "paid_at": datetime.utcnow().isoformat()}})
    except: pass
    artwork_id = get_metadata(intent, "artwork_id")
    try:
        art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
        if art:
            artworks_col.update_one({"_id": ObjectId(artwork_id)}, {"$set": {"status": "sold"}})
            payments_col.insert_one({
                "user_id": str(current_user["_id"]),
                "buyer_name": f"{current_user['first_name']} {current_user['last_name']}",
                "artwork_id": artwork_id,
                "art_title": art["title"],
                "artist_id": art["artist_id"],
                "artist_name": art["artist_name"],
                "amount": int(float(art["price"]) * 100),
                "amount_inr": float(art["price"]),
                "stripe_pi_id": payment_intent_id,
                "type": "artwork_sale",
                "status": "completed",
                "created_at": datetime.utcnow().isoformat(),
                "paid_at": datetime.utcnow().isoformat()
            })
            push_notification(art["artist_id"],
                f"🎨 {current_user['first_name']} {current_user['last_name']} bought '{art['title']}' — ₹{art['price']} earned!")
    except: pass
    return {"message": "Payment confirmed", "artwork_id": artwork_id}

# ── PAYMENTS — TUTORIAL (PaymentIntent — no redirect) ✨ ───────
@app.post("/payments/tutorial/intent")
def create_tutorial_intent(tutorial_id: str=Form(...), current_user=Depends(get_current_user)):
    try: tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
    except: raise HTTPException(404, "Tutorial not found")
    if not tut: raise HTTPException(404, "Tutorial not found")
    if payments_col.find_one({"user_id": str(current_user["_id"]), "tutorial_id": tutorial_id, "status": "completed"}):
        raise HTTPException(400, "Already purchased")
    intent = stripe.PaymentIntent.create(
        amount=int(float(tut["price"]) * 100), currency="inr",
        description=f"Tutorial: {tut['title']}", payment_method_types=["card"],
        metadata={"tutorial_id": tutorial_id, "user_id": str(current_user["_id"]), "type": "tutorial"})
    payments_col.insert_one({"user_id": str(current_user["_id"]), "tutorial_id": tutorial_id,
                              "type": "tutorial", "amount": float(tut["price"]),
                              "stripe_pi_id": get_intent_field(intent, "id"), "status": "pending",
                              "created_at": datetime.utcnow().isoformat()})
    return {"client_secret": get_intent_field(intent, "client_secret"), "tutorial_id": tutorial_id}

@app.post("/payments/tutorial/intent/confirm")
def confirm_tutorial_intent(payment_intent_id: str=Form(...), tutorial_id: str=Form(...),
                              current_user=Depends(get_current_user)):
    try: intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e: raise HTTPException(400, str(e))
    if get_intent_field(intent, "status") != "succeeded":
        raise HTTPException(400, f"Payment not completed: {get_intent_field(intent, 'status')}")
    payments_col.update_one({"stripe_pi_id": payment_intent_id},
        {"$set": {"status": "completed", "paid_at": datetime.utcnow().isoformat()}})
    try:
        tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
        if tut:
            tutorials_col.update_one({"_id": ObjectId(tutorial_id)},
                {"$inc": {"students": 1, "earnings": float(tut["price"])}})
            push_notification(tut["artist_id"],
                f"🎬 {current_user['first_name']} {current_user['last_name']} purchased '{tut['title']}' — ₹{tut['price']} earned!")
    except: pass
    return {"message": "Tutorial unlocked", "tutorial_id": tutorial_id}

# ── PAYMENTS — ARTWORK (Checkout redirect — legacy) ────────────
@app.post("/payments/artwork/checkout")
def create_artwork_checkout(artwork_id: str=Form(...), address: str=Form(...), phone: str=Form(...),
    note: str=Form(""), payment_type: str=Form("online"), current_user=Depends(get_current_user)):
    try: art = artworks_col.find_one({"_id": ObjectId(artwork_id)})
    except: raise HTTPException(404, "Artwork not found")
    if not art or art["status"] != "listed": raise HTTPException(400, "Artwork not available")
    order = {"artwork_id": artwork_id, "art_title": art["title"], "art_image_url": art.get("image_url"),
             "artist_id": art["artist_id"], "artist_name": art["artist_name"],
             "buyer_id": str(current_user["_id"]),
             "buyer_name": f"{current_user['first_name']} {current_user['last_name']}",
             "buyer_email": current_user["email"], "address": address, "phone": phone, "note": note,
             "amount": float(art["price"]), "payment_type": payment_type,
             "status": "pending", "created_at": datetime.utcnow().isoformat()}
    if payment_type == "cod":
        result = orders_col.insert_one(order)
        push_notification(art["artist_id"], f"🛒 New COD order for '{art['title']}' from {order['buyer_name']}!")
        return {"order_id": str(result.inserted_id), "message": "COD order placed"}
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price_data": {"currency": "inr", "unit_amount": int(float(art["price"]) * 100),
                                     "product_data": {"name": art["title"]}}, "quantity": 1}],
        mode="payment",
        success_url=f"{FRONTEND_URL}/customer.html?session_id={{CHECKOUT_SESSION_ID}}&type=artwork&id={artwork_id}",
        cancel_url=f"{FRONTEND_URL}/customer.html",
        metadata={"artwork_id": artwork_id, "user_id": str(current_user["_id"]), "type": "artwork"})
    order["stripe_session_id"] = get_intent_field(session, "id")
    result = orders_col.insert_one(order)
    return {"checkout_url": get_intent_field(session, "url"), "order_id": str(result.inserted_id)}

@app.post("/payments/artwork/verify")
def verify_artwork_payment(session_id: str=Form(...), current_user=Depends(get_current_user)):
    try: session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e: raise HTTPException(400, str(e))
    if get_intent_field(session, "payment_status") != "paid":
        raise HTTPException(400, "Payment not completed")
    artwork_id = get_metadata(session, "artwork_id")
    orders_col.update_one({"stripe_session_id": session_id},
        {"$set": {"status": "approved", "paid_at": datetime.utcnow().isoformat()}})
    try:
        artworks_col.update_one({"_id": ObjectId(artwork_id)}, {"$set": {"status": "sold"}})
        art2 = artworks_col.find_one({"_id": ObjectId(artwork_id)})
        if art2:
            push_notification(art2["artist_id"],
                f"🎨 {current_user['first_name']} {current_user['last_name']} bought '{art2['title']}' — ₹{art2['price']} earned!")
    except: pass
    return {"message": "Payment verified", "artwork_id": artwork_id}

# ── PAYMENTS — TUTORIAL (Checkout redirect — legacy) ──────────
@app.post("/payments/tutorial/checkout")
def create_tutorial_checkout(tutorial_id: str=Form(...), current_user=Depends(get_current_user)):
    try: tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
    except: raise HTTPException(404, "Tutorial not found")
    if not tut: raise HTTPException(404, "Tutorial not found")
    if payments_col.find_one({"user_id": str(current_user["_id"]), "tutorial_id": tutorial_id, "status": "completed"}):
        raise HTTPException(400, "Already purchased")
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price_data": {"currency": "inr", "unit_amount": int(float(tut["price"]) * 100),
                                     "product_data": {"name": tut["title"], "description": f"Tutorial by {tut['artist_name']}"}},
                     "quantity": 1}],
        mode="payment",
        success_url=f"{FRONTEND_URL}/customer.html?session_id={{CHECKOUT_SESSION_ID}}&type=tutorial&id={tutorial_id}",
        cancel_url=f"{FRONTEND_URL}/customer.html",
        metadata={"tutorial_id": tutorial_id, "user_id": str(current_user["_id"]), "type": "tutorial"})
    payments_col.insert_one({"user_id": str(current_user["_id"]), "tutorial_id": tutorial_id,
                              "type": "tutorial", "amount": float(tut["price"]),
                              "stripe_session_id": get_intent_field(session, "id"), "status": "pending",
                              "created_at": datetime.utcnow().isoformat()})
    return {"checkout_url": get_intent_field(session, "url"), "session_id": get_intent_field(session, "id")}

@app.post("/payments/tutorial/verify")
def verify_tutorial_payment(session_id: str=Form(...), current_user=Depends(get_current_user)):
    try: session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e: raise HTTPException(400, str(e))
    if get_intent_field(session, "payment_status") != "paid":
        raise HTTPException(400, "Payment not completed")
    tutorial_id = get_metadata(session, "tutorial_id")
    payments_col.update_one({"stripe_session_id": session_id},
        {"$set": {"status": "completed", "paid_at": datetime.utcnow().isoformat()}})
    try:
        tut = tutorials_col.find_one({"_id": ObjectId(tutorial_id)})
        if tut:
            tutorials_col.update_one({"_id": ObjectId(tutorial_id)},
                {"$inc": {"students": 1, "earnings": float(tut["price"])}})
            push_notification(tut["artist_id"],
                f"🎬 {current_user['first_name']} {current_user['last_name']} purchased '{tut['title']}' — ₹{tut['price']} earned!")
    except: pass
    return {"message": "Payment verified", "tutorial_id": tutorial_id}

# ── STRIPE WEBHOOK ────────────────────────────────────────────
@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if webhook_secret:
        try: event = stripe.Webhook.construct_event(payload, request.headers.get("stripe-signature", ""), webhook_secret)
        except: raise HTTPException(400, "Invalid signature")
    else:
        import json; event = json.loads(payload)
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata") or {}
        pt = meta.get("type")
        if pt == "tutorial":
            tid = meta.get("tutorial_id")
            payments_col.update_one({"stripe_session_id": session["id"]},
                {"$set": {"status": "completed", "paid_at": datetime.utcnow().isoformat()}})
            try:
                tut = tutorials_col.find_one({"_id": ObjectId(tid)})
                if tut:
                    tutorials_col.update_one({"_id": ObjectId(tid)},
                        {"$inc": {"students": 1, "earnings": float(tut["price"])}})
                    push_notification(tut["artist_id"], f"🎬 Someone purchased '{tut['title']}' — ₹{tut['price']} earned!")
            except: pass
        elif pt == "artwork":
            aid = meta.get("artwork_id")
            orders_col.update_one({"stripe_session_id": session["id"]},
                {"$set": {"status": "approved", "paid_at": datetime.utcnow().isoformat()}})
            try:
                art2 = artworks_col.find_one({"_id": ObjectId(aid)})
                if art2:
                    artworks_col.update_one({"_id": ObjectId(aid)}, {"$set": {"status": "sold"}})
                    push_notification(art2["artist_id"], f"🎨 '{art2['title']}' sold! — ₹{art2['price']} earned!")
            except: pass
    return {"received": True}

# ── ORDERS ────────────────────────────────────────────────────
@app.get("/orders/mine")
def my_orders_as_buyer(current_user=Depends(get_current_user)):
    return [to_str_id(o) for o in orders_col.find({"buyer_id": str(current_user["_id"])}).sort("created_at", -1)]

@app.get("/orders/artist")
def my_orders_as_artist(current_user=Depends(get_current_user)):
    if current_user["role"] != "artist": raise HTTPException(403, "Artists only")
    return [to_str_id(o) for o in orders_col.find({"artist_id": str(current_user["_id"])}).sort("created_at", -1)]

@app.put("/orders/{order_id}/status")
def update_order_status(order_id: str, status: str=Form(...), current_user=Depends(get_current_user)):
    try: order = orders_col.find_one({"_id": ObjectId(order_id)})
    except: raise HTTPException(404, "Not found")
    if not order: raise HTTPException(404, "Order not found")
    if current_user["role"] == "artist" and order["artist_id"] != str(current_user["_id"]): raise HTTPException(403, "Not your order")
    if current_user["role"] == "customer" and order["buyer_id"] != str(current_user["_id"]): raise HTTPException(403, "Not your order")
    orders_col.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": status}})
    msgs = {"approved": (order["buyer_id"], f"✅ Your order for '{order['art_title']}' was approved!"),
            "rejected": (order["buyer_id"], f"❌ Your order for '{order['art_title']}' was rejected."),
            "shipped":  (order["buyer_id"], f"📦 Your order '{order['art_title']}' has been shipped!"),
            "delivered":(order["artist_id"],f"🎉 Order '{order['art_title']}' marked as delivered.")}
    if status in msgs: push_notification(*msgs[status])
    return {"message": f"Order {status}"}

# ── JOBS ──────────────────────────────────────────────────────
@app.post("/jobs")
def create_job(title: str=Form(...), budget: str=Form(...), job_type: str=Form("Freelance"),
    location: str=Form("Remote"), dept: str=Form(""), deadline: str=Form(""),
    skills: str=Form(""), desc: str=Form(""), status: str=Form("active"),
    current_user=Depends(get_current_user)):
    if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
    job = {"brand_id": str(current_user["_id"]),
           "brand_name": current_user.get("brand_name") or f"{current_user['first_name']} {current_user['last_name']}",
           "title": title, "budget": budget, "job_type": job_type, "location": location,
           "dept": dept, "deadline": deadline,
           "skills": [s.strip() for s in skills.split(",") if s.strip()],
           "desc": desc, "status": status, "created_at": datetime.utcnow().isoformat()}
    result = jobs_col.insert_one(job); job["_id"] = str(result.inserted_id)
    return job

@app.get("/jobs")
def list_jobs(status: Optional[str]="active"):
    query = {"status": status} if status else {}
    return [to_str_id(j) for j in jobs_col.find(query).sort("created_at", -1)]

@app.put("/jobs/{job_id}")
def update_job(job_id: str, title: Optional[str]=Form(None), budget: Optional[str]=Form(None),
    job_type: Optional[str]=Form(None), location: Optional[str]=Form(None),
    skills: Optional[str]=Form(None), desc: Optional[str]=Form(None),
    current_user=Depends(get_current_user)):
    if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
    update = {k: v for k, v in {"title": title, "budget": budget, "job_type": job_type,
                                  "location": location, "desc": desc}.items() if v is not None}
    if skills is not None: update["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
    if update: jobs_col.update_one({"_id": ObjectId(job_id)}, {"$set": update})
    return to_str_id(jobs_col.find_one({"_id": ObjectId(job_id)}))

@app.delete("/jobs/{job_id}")
def delete_job(job_id: str, current_user=Depends(get_current_user)):
    if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
    jobs_col.delete_one({"_id": ObjectId(job_id)})
    db["applications"].delete_many({"job_id": job_id})
    return {"message": "Deleted"}

@app.post("/jobs/{job_id}/apply")
def apply_to_job(job_id: str, message: str=Form(""), current_user=Depends(get_current_user)):
    if current_user["role"] != "artist": raise HTTPException(403, "Artists only")
    try: job = jobs_col.find_one({"_id": ObjectId(job_id)})
    except: raise HTTPException(404, "Job not found")
    if not job: raise HTTPException(404, "Job not found")
    if db["applications"].find_one({"job_id": job_id, "artist_id": str(current_user["_id"])}):
        raise HTTPException(400, "Already applied")
    app_doc = {"job_id": job_id, "job_title": job["title"], "brand_id": job["brand_id"],
               "artist_id": str(current_user["_id"]),
               "artist_name": f"{current_user['first_name']} {current_user['last_name']}",
               "artist_avatar": current_user.get("avatar_url"),
               "skills": current_user.get("skills", []), "city": current_user.get("city", ""),
               "medium": current_user.get("medium", ""), "message": message,
               "status": "pending", "applied_at": datetime.utcnow().isoformat()}
    db["applications"].insert_one(app_doc)
    push_notification(job["brand_id"], f"🎨 New application from {app_doc['artist_name']} for '{job['title']}'")
    return {"message": "Application sent"}

@app.get("/jobs/applications")
def get_applications(current_user=Depends(get_current_user)):
    uid = str(current_user["_id"])
    query = {"brand_id": uid} if current_user["role"] == "brand" else {"artist_id": uid}
    return [to_str_id(a) for a in db["applications"].find(query).sort("applied_at", -1)]

@app.get("/jobs/{job_id}/applications")
def get_job_applications(job_id: str, current_user=Depends(get_current_user)):
    if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
    return [to_str_id(a) for a in db["applications"].find({"job_id": job_id})]

@app.put("/jobs/applications/{app_id}/status")
def update_application_status(app_id: str, status: str=Form(...), current_user=Depends(get_current_user)):
    if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
    try: db["applications"].update_one({"_id": ObjectId(app_id)}, {"$set": {"status": status}})
    except: raise HTTPException(404, "Application not found")
    return {"message": f"Status updated to {status}"}

# ── COMPETITIONS ──────────────────────────────────────────────
@app.post("/competitions")
def create_competition(title: str=Form(...), prize: str=Form(...), category: str=Form("Other"),
    start_date: str=Form(""), end_date: str=Form(""), desc: str=Form(""), tags: str=Form(""),
    current_user=Depends(get_current_user)):
    if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
    comp = {"brand_id": str(current_user["_id"]),
            "brand_name": current_user.get("brand_name") or f"{current_user['first_name']} {current_user['last_name']}",
            "title": title, "prize": prize, "category": category, "start_date": start_date,
            "end_date": end_date, "desc": desc,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "entries": 0, "status": "active", "created_at": datetime.utcnow().isoformat()}
    result = db["competitions"].insert_one(comp); comp["_id"] = str(result.inserted_id)
    return comp

@app.get("/competitions")
def list_competitions(status: Optional[str]="active", brand_id: Optional[str]=None):
    query = {}
    if status: query["status"] = status
    if brand_id: query["brand_id"] = brand_id
    return [to_str_id(c) for c in db["competitions"].find(query).sort("created_at", -1)]

@app.get("/competitions/mine/registered")
def my_registered_competitions(current_user=Depends(get_current_user)):
    return [{"comp_id": r["comp_id"]} for r in db["comp_registrations"].find({"artist_id": str(current_user["_id"])})]

@app.get("/competitions/{comp_id}/registrations")
def get_competition_registrations(comp_id: str, current_user=Depends(get_current_user)):
    return [{"artist_id": r.get("artist_id"), "artist_name": r.get("artist_name"),
             "registered_at": r.get("registered_at")} for r in db["comp_registrations"].find({"comp_id": comp_id})]

@app.post("/competitions/{comp_id}/register")
def register_competition(comp_id: str, current_user=Depends(get_current_user)):
    if current_user["role"] != "artist": raise HTTPException(403, "Artists only")
    if db["comp_registrations"].find_one({"comp_id": comp_id, "artist_id": str(current_user["_id"])}):
        raise HTTPException(400, "Already registered")
    db["comp_registrations"].insert_one({"comp_id": comp_id, "artist_id": str(current_user["_id"]),
        "artist_name": f"{current_user['first_name']} {current_user['last_name']}",
        "registered_at": datetime.utcnow().isoformat()})
    try:
        db["competitions"].update_one({"_id": ObjectId(comp_id)}, {"$inc": {"entries": 1}})
        comp_doc = db["competitions"].find_one({"_id": ObjectId(comp_id)})
        if comp_doc: push_notification(comp_doc["brand_id"],
            f"🏆 {current_user['first_name']} {current_user['last_name']} registered for '{comp_doc['title']}'")
    except: pass
    return {"message": "Registered"}

# ── MESSAGES ─────────────────────────────────────────────────
@app.post("/messages/send")
def send_message(recipient_id: str=Form(...), body: str=Form(...), current_user=Depends(get_current_user)):
    sender_id = str(current_user["_id"])
    thread_id = "_".join(sorted([sender_id, recipient_id]))
    messages_col.insert_one({"thread_id": thread_id, "from_id": sender_id, "to_id": recipient_id,
        "from_name": f"{current_user['first_name']} {current_user['last_name']}",
        "body": body, "read": False, "created_at": datetime.utcnow().isoformat()})
    return {"message": "Sent", "thread_id": thread_id}

@app.get("/messages/threads")
def my_threads(current_user=Depends(get_current_user)):
    user_id = str(current_user["_id"])
    msgs    = list(messages_col.find({"$or": [{"from_id": user_id}, {"to_id": user_id}]}).sort("created_at", -1))
    threads = {}
    for m in msgs:
        tid = m["thread_id"]
        if tid not in threads:
            other_id = m["to_id"] if m["from_id"] == user_id else m["from_id"]
            other    = users_col.find_one({"_id": ObjectId(other_id)}) if other_id else None
            threads[tid] = {"thread_id": tid,
                "other_user": {"id": other_id,
                               "name": f"{other['first_name']} {other['last_name']}" if other else "Unknown",
                               "avatar_url": other.get("avatar_url") if other else None,
                               "role": other.get("role") if other else ""} if other else {},
                "last_message": to_str_id(m), "unread_count": 0}
        if m["to_id"] == user_id and not m["read"]: threads[tid]["unread_count"] += 1
    return list(threads.values())

@app.get("/messages/thread/{thread_id}")
def get_thread(thread_id: str, current_user=Depends(get_current_user)):
    user_id = str(current_user["_id"])
    if user_id not in thread_id.split("_"): raise HTTPException(403, "Not your thread")
    msgs = [to_str_id(m) for m in messages_col.find({"thread_id": thread_id}).sort("created_at", 1)]
    messages_col.update_many({"thread_id": thread_id, "to_id": user_id, "read": False}, {"$set": {"read": True}})
    return msgs

# ── NOTIFICATIONS ─────────────────────────────────────────────
@app.get("/notifications")
def get_notifications(current_user=Depends(get_current_user)):
    return [to_str_id(n) for n in notifs_col.find({"user_id": str(current_user["_id"])}).sort("created_at", -1).limit(50)]

@app.put("/notifications/read-all")
def mark_all_notifications_read(current_user=Depends(get_current_user)):
    notifs_col.update_many({"user_id": str(current_user["_id"]), "read": False}, {"$set": {"read": True}})
    return {"message": "All marked as read"}

# ── ARTISTS ───────────────────────────────────────────────────
@app.get("/artists")
def search_artists(search: Optional[str]=None, medium: Optional[str]=None, city: Optional[str]=None):
    query: dict = {"role": "artist"}
    if medium: query["medium"] = {"$regex": medium, "$options": "i"}
    if city:   query["city"]   = {"$regex": city,   "$options": "i"}
    if search:
        query["$or"] = [{"first_name": {"$regex": search, "$options": "i"}},
                        {"last_name":  {"$regex": search, "$options": "i"}},
                        {"medium":     {"$regex": search, "$options": "i"}},
                        {"city":       {"$regex": search, "$options": "i"}},
                        {"skills":     {"$in": [search]}}]
    artists = []
    for u in users_col.find(query):
        u = to_str_id(u); u.pop("password_hash", None); u.pop("session_token", None)
        u["listed_artworks"] = artworks_col.count_documents({"artist_id": u["_id"], "status": "listed"})
        artists.append(u)
    return artists

@app.get("/artists/{artist_id}")
def get_artist_profile(artist_id: str):
    try: user = users_col.find_one({"_id": ObjectId(artist_id), "role": "artist"})
    except: raise HTTPException(404, "Not found")
    if not user: raise HTTPException(404, "Artist not found")
    user = to_str_id(user); user.pop("password_hash", None); user.pop("session_token", None)
    user["artworks"] = [to_str_id(a) for a in artworks_col.find({"artist_id": artist_id, "status": "listed"})]
    tuts = []
    for t in tutorials_col.find({"artist_id": artist_id}):
        t = to_str_id(t); t.pop("video_url", None); tuts.append(t)
    user["tutorials"] = tuts
    return user

# ── BRAND PAYMENTS ────────────────────────────────────────────
@app.post("/payments/brand/pay-artist")
def brand_pay_artist(artist_id: str=Form(...), amount: float=Form(...),
    desc: str=Form("Job Payment"), notes: str=Form(""), current_user=Depends(get_current_user)):
    if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
    try: artist = users_col.find_one({"_id": ObjectId(artist_id), "role": "artist"})
    except: raise HTTPException(404, "Artist not found")
    if not artist: raise HTTPException(404, "Artist not found")
    artist_name = f"{artist['first_name']} {artist['last_name']}"
    brand_name  = current_user.get("brand_name") or f"{current_user['first_name']} {current_user['last_name']}"
    amount_paise = int(float(amount))
    intent = stripe.PaymentIntent.create(amount=amount_paise, currency="inr",
        description=f"{desc} — {artist_name} (ArtCraft)", payment_method_types=["card"],
        metadata={"brand_id": str(current_user["_id"]), "artist_id": artist_id,
                  "artist_name": artist_name, "desc": desc, "type": "brand_payment"})
    intent_id     = get_intent_field(intent, "id")
    client_secret = get_intent_field(intent, "client_secret")
    payments_col.insert_one({"brand_id": str(current_user["_id"]), "brand_name": brand_name,
        "artist_id": artist_id, "artist_name": artist_name, "amount": amount_paise,
        "desc": desc, "notes": notes, "stripe_pi_id": intent_id, "client_secret": client_secret,
        "type": "brand_payment", "status": "pending", "created_at": datetime.utcnow().isoformat()})
    return {"client_secret": client_secret, "payment_intent_id": intent_id,
            "amount_paise": amount_paise, "artist_name": artist_name}

@app.post("/payments/brand/confirm")
def confirm_brand_payment(payment_intent_id: str=Form(...), current_user=Depends(get_current_user)):
    if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
    try: intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e: raise HTTPException(400, str(e))
    if get_intent_field(intent, "status") != "succeeded":
        raise HTTPException(400, f"Payment not succeeded: {get_intent_field(intent, 'status')}")
    pay_record = payments_col.find_one_and_update({"stripe_pi_id": payment_intent_id},
        {"$set": {"status": "completed", "paid_at": datetime.utcnow().isoformat()}})
    if pay_record:
        amount_inr = int(pay_record.get("amount", 0)) // 100
        push_notification(pay_record["artist_id"],
            f"💰 {pay_record['brand_name']} sent you ₹{amount_inr:,} — '{pay_record['desc']}'")
    return {"message": "Payment confirmed"}

@app.get("/payments/brand/history")
def brand_payment_history(current_user=Depends(get_current_user)):
    if current_user["role"] != "brand": raise HTTPException(403, "Brands only")
    pays = []
    for p in payments_col.find({"brand_id": str(current_user["_id"]), "type": "brand_payment"}).sort("created_at", -1):
        p = to_str_id(p)
        raw = p.get("amount", 0)
        p["amount_inr"] = int(raw) // 100 if raw > 1000 else int(raw)
        pays.append(p)
    return pays

@app.get("/payments/artist/received")
def artist_received_payments(current_user=Depends(get_current_user)):
    return [to_str_id(p) for p in payments_col.find(
        {"artist_id": str(current_user["_id"]), "type": "brand_payment", "status": "completed"}).sort("paid_at", -1)]

# ── AI CHAT ───────────────────────────────────────────────────
class AIChatRequest(BaseModel):
    messages: List[dict]

@app.post("/ai/chat")
async def ai_chat(body: AIChatRequest, current_user=Depends(get_current_user)):
    if not GROQ_API_KEY: raise HTTPException(500, "AI service not configured — add GROQ_API_KEY to .env")
    groq_messages = [{"role": "system", "content": ARTCRAFT_AI_SYSTEM}] + body.messages
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(GROQ_CHAT_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": groq_messages, "max_tokens": 300, "temperature": 0.7})
        resp.raise_for_status()
        return {"reply": resp.json()["choices"][0]["message"]["content"]}
    except httpx.HTTPStatusError as e: raise HTTPException(502, f"Groq API error: {e.response.text[:200]}")
    except Exception as e: raise HTTPException(502, f"AI service unavailable: {str(e)}")

@app.get("/config/stripe")
def get_stripe_config():
    pk = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_51TFUEsAkOvpUa6hU6G5cJIq9DFNZ7rEpwzVGxgFIjg0Kxzdqz6qtyOAW5ehNkGwrQa5CEUHnMBEUP5J7b2s3cHOG00Rgban7QN")
    if not pk:
        raise HTTPException(500, "Stripe publishable key not configured")
    return {"publishable_key": pk}

# ── HEALTH ────────────────────────────────────────────────────
@app.get("/")
def root(): return {"app": "ArtCraft API", "version": "1.0.0", "status": "running", "docs": "/docs"}

@app.get("/health")
def health():
    try: client.admin.command("ping"); db_ok = True
    except: db_ok = False
    return {"api": "ok", "mongodb": "ok" if db_ok else "error"}