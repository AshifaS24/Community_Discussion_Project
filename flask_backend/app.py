# from curses import flash
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from discourse_api import get_latest_topics, get_topic_discussion
import secrets
import sqlite3
import re
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session, jsonify, flash,url_for
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "community.db"
app = Flask(__name__)
app.secret_key = "mysecretkey"

# ==================================================
# ROOT ROUTE
# ==================================================

@app.route("/")
def index():

    if "user" in session:
        return redirect(url_for("home"))

    return redirect(url_for("login"))

# ==================================================
# USER REGISTRATION
# ==================================================

# ==================================================
# USER REGISTRATION
# ==================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # ==========================================
        # GET FORM DATA
        # ==========================================

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]


        # ==========================================
        # BASIC VALIDATION
        # ==========================================

        if not name:

            return render_template(
                "register.html",
                error="Please enter your name.",
                entered_name=name,
                entered_email=email
            )


        if not email:

            return render_template(
                "register.html",
                error="Please enter your email address.",
                entered_name=name,
                entered_email=email
            )


        # ==========================================
        # STRONG PASSWORD VALIDATION
        # ==========================================

        # Minimum 8 characters
        if len(password) < 8:

            return render_template(
                "register.html",
                error="Password must contain at least 8 characters.",
                entered_name=name,
                entered_email=email
            )


        # At least one uppercase letter
        if not re.search(r"[A-Z]", password):

            return render_template(
                "register.html",
                error="Password must contain at least one uppercase letter.",
                entered_name=name,
                entered_email=email
            )


        # At least one lowercase letter
        if not re.search(r"[a-z]", password):

            return render_template(
                "register.html",
                error="Password must contain at least one lowercase letter.",
                entered_name=name,
                entered_email=email
            )


        # At least one number
        if not re.search(r"[0-9]", password):

            return render_template(
                "register.html",
                error="Password must contain at least one number.",
                entered_name=name,
                entered_email=email
            )


        # At least one special character
        if not re.search(r"[^A-Za-z0-9]", password):

            return render_template(
                "register.html",
                error="Password must contain at least one special character.",
                entered_name=name,
                entered_email=email
            )


        # No spaces
        if re.search(r"\s", password):

            return render_template(
                "register.html",
                error="Password must not contain spaces.",
                entered_name=name,
                entered_email=email
            )


        # ==========================================
        # CONNECT DATABASE
        # ==========================================

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()


        # ==========================================
        # CHECK IF EMAIL ALREADY EXISTS
        # ==========================================

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(email) = ?
            """,
            (email,)
        )

        existing_user = cursor.fetchone()


        if existing_user:

            conn.close()

            return render_template(
                "register.html",
                error="An account with this email already exists.",
                entered_name=name,
                entered_email=email
            )


        # ==========================================
        # GENERATE UNIQUE KDISC USER ID
        # ==========================================

        while True:

            user_id = (
                "KD-" +
                secrets.token_hex(4).upper()
            )

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE user_id = ?
                """,
                (user_id,)
            )

            existing_user_id = cursor.fetchone()

            if existing_user_id is None:
                break


        # ==========================================
        # HASH PASSWORD
        # ==========================================

        hashed_password = generate_password_hash(
            password
        )


        # ==========================================
        # CREATE NORMAL USER
        # ==========================================

        cursor.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password,
                role,
                user_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                hashed_password,
                "user",
                user_id
            )
        )


        # ==========================================
        # SAVE DATABASE
        # ==========================================

        conn.commit()
        conn.close()


        # ==========================================
        # REGISTRATION SUCCESS
        # ==========================================

        return render_template(
            "register_success.html",
            user_id=user_id
        )


    # ==========================================
    # OPEN REGISTRATION PAGE
    # ==========================================

    return render_template(
        "register.html"
    )
# ==================================================
# USER LOGIN
# ==================================================

# ==================================================
# USER LOGIN
# ==================================================

# ==================================================
# USER LOGIN
# ==================================================

# ==================================================
# USER LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        # ==========================================
        # GET LOGIN DETAILS
        # ==========================================

        email = request.form["email"].strip().lower()
        password = request.form["password"]


        # ==========================================
        # CONNECT DATABASE
        # ==========================================

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()


        # ==========================================
        # FIND USER
        # ==========================================

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password,
                role,
                user_id
            FROM users
            WHERE LOWER(email) = ?
            ORDER BY id DESC
            """,
            (email,)
        )

        users = cursor.fetchall()


        # ==========================================
        # FIND MATCHING PASSWORD
        # Supports:
        #   1. New hashed passwords
        #   2. Old plaintext passwords
        # ==========================================

        user = None
        old_password_format = False

        for candidate in users:

            stored_password = candidate[3]

            # --------------------------------------
            # NEW HASHED PASSWORD
            # --------------------------------------

            if stored_password.startswith(
                ("scrypt:", "pbkdf2:")
            ):

                try:

                    if check_password_hash(
                        stored_password,
                        password
                    ):
                        user = candidate
                        break

                except ValueError:
                    pass


            # --------------------------------------
            # OLD PLAINTEXT PASSWORD
            # --------------------------------------

            else:

                if stored_password == password:

                    user = candidate
                    old_password_format = True
                    break


        # ==========================================
        # LOGIN SUCCESS
        # ==========================================

        if user:

            # ======================================
            # AUTOMATICALLY UPGRADE OLD PASSWORD
            # ======================================

            if old_password_format:

                new_password_hash = generate_password_hash(
                    password
                )

                cursor.execute(
                    """
                    UPDATE users
                    SET password = ?
                    WHERE id = ?
                    """,
                    (
                        new_password_hash,
                        user[0]
                    )
                )

                conn.commit()


            conn.close()


            # ======================================
            # CREATE SESSION
            # ======================================

            session.clear()

            session["user"] = user[2]
            session["user_id"] = user[5]
            session["name"] = user[1]
            session["role"] = user[4]


            # ======================================
            # ADMIN
            # ======================================

            if user[4] == "admin":

                return redirect(
                    url_for("admin_dashboard")
                )


            # ======================================
            # NORMAL USER
            # ======================================

            return redirect(
                url_for("home")
            )


        # ==========================================
        # LOGIN FAILED
        # ==========================================

        conn.close()

        return render_template(
            "login.html",
            error="Email or password is incorrect.",
            entered_email=email
        )


    # ==============================================
    # OPEN LOGIN PAGE
    # ==============================================

    return render_template(
        "login.html"
    )
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM discussions")
    total_discussions = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(likes) FROM discussions")
    total_likes = cursor.fetchone()[0] or 0

    conn.close()

    return render_template(
        "dashboard.html",
        total_users=total_users,
        total_discussions=total_discussions,
        total_likes=total_likes
    )
# ==================================================
# NORMAL USER HOME
# ==================================================

# ==================================================
# NORMAL USER HOME
# ==================================================

# ==================================================
# NORMAL USER HOME
# ==================================================

@app.route("/home")
def home():

    # ==========================================
    # LOGIN REQUIRED
    # ==========================================

    if "user" not in session:
        return redirect(url_for("login"))


    # ==========================================
    # LOGGED-IN USER INFORMATION
    # ==========================================

    user_email = session.get("user")
    user_name = session.get("name")
    user_id = session.get("user_id")
    user_role = session.get("role", "user")


    # ==========================================
    # ADMIN MUST USE ADMIN DASHBOARD
    # ==========================================

    if user_role == "admin":

        return redirect(
            url_for("admin_dashboard")
        )


    # ==========================================
    # DATABASE CONNECTION
    # ==========================================

    conn = sqlite3.connect(DB_PATH)

    # Allows us to use:
    # discussion["title"]
    # instead of discussion[1]

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()


    # ==========================================
    # 1. USER'S DISCUSSION COUNT
    # ==========================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM discussions
        WHERE LOWER(owner) = LOWER(?)
        """,
        (user_email,)
    )

    my_discussions = cursor.fetchone()[0]


    # ==========================================
    # 2. USER'S COMMENT COUNT
    # ==========================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM comments
        WHERE LOWER(author) = LOWER(?)
        """,
        (user_email,)
    )

    my_comments = cursor.fetchone()[0]


    # ==========================================
    # 3. USER'S SAVED DISCUSSIONS
    # ==========================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM bookmarks
        WHERE LOWER(user_email) = LOWER(?)
        """,
        (user_email,)
    )

    my_bookmarks = cursor.fetchone()[0]


    # ==========================================
    # 4. DISCUSSIONS LIKED BY USER
    # ==========================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM likes
        WHERE LOWER(user_email) = LOWER(?)
        """,
        (user_email,)
    )

    my_likes = cursor.fetchone()[0]


    # ==========================================
    # 5. LIKES RECEIVED ON USER'S DISCUSSIONS
    # ==========================================

    cursor.execute(
        """
        SELECT COALESCE(SUM(likes), 0)
        FROM discussions
        WHERE LOWER(owner) = LOWER(?)
        """,
        (user_email,)
    )

    likes_received = cursor.fetchone()[0]


    # ==========================================
    # 6. LATEST COMMUNITY DISCUSSIONS
    # ==========================================

    cursor.execute(
        """
        SELECT
            id,
            title,
            content,
            owner,
            likes,
            status
        FROM discussions
        ORDER BY id DESC
        LIMIT 6
        """
    )

    latest_discussions = cursor.fetchall()


    # ==========================================
    # 7. TRENDING DISCUSSIONS
    #
    # Currently determined using the existing
    # discussion likes value.
    # ==========================================

    cursor.execute(
        """
        SELECT
            id,
            title,
            content,
            owner,
            likes,
            status
        FROM discussions
        ORDER BY likes DESC, id DESC
        LIMIT 5
        """
    )

    trending_discussions = cursor.fetchall()


    # ==========================================
    # 8. USER'S RECENT DISCUSSIONS
    # ==========================================

    cursor.execute(
        """
        SELECT
            id,
            title,
            content,
            owner,
            likes,
            status
        FROM discussions
        WHERE LOWER(owner) = LOWER(?)
        ORDER BY id DESC
        LIMIT 4
        """,
        (user_email,)
    )

    user_recent_discussions = cursor.fetchall()


    # ==========================================
    # 9. USER'S BOOKMARKED DISCUSSIONS
    # ==========================================

    cursor.execute(
        """
        SELECT
            d.id,
            d.title,
            d.content,
            d.owner,
            d.likes,
            d.status
        FROM bookmarks AS b

        JOIN discussions AS d
            ON d.id = b.discussion_id

        WHERE LOWER(b.user_email) = LOWER(?)

        ORDER BY b.id DESC

        LIMIT 4
        """,
        (user_email,)
    )

    saved_discussions = cursor.fetchall()


    # ==========================================
    # 10. RECENT COMMUNITY ACTIVITY
    # ==========================================

    cursor.execute(
        """
        SELECT
            id,
            activity
        FROM activity
        ORDER BY id DESC
        LIMIT 6
        """
    )

    recent_activity = cursor.fetchall()


    # ==========================================
    # 11. COMMUNITY TOTALS
    #
    # These are only used for a small
    # Community Pulse area — not admin analytics.
    # ==========================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        """
    )

    community_members = cursor.fetchone()[0]


    cursor.execute(
        """
        SELECT COUNT(*)
        FROM discussions
        """
    )

    community_discussions = cursor.fetchone()[0]


    # ==========================================
    # CLOSE DATABASE
    # ==========================================

    conn.close()


    # ==========================================
    # OPEN USER 3D HOME PAGE
    # ==========================================

    return render_template(
        "home.html",

        # Logged-in user
        current_user=user_email,
        user_name=user_name,
        user_id=user_id,
        user_role=user_role,

        # Personal statistics
        my_discussions=my_discussions,
        my_comments=my_comments,
        my_bookmarks=my_bookmarks,
        my_likes=my_likes,
        likes_received=likes_received,

        # Discussion content
        latest_discussions=latest_discussions,
        trending_discussions=trending_discussions,
        user_recent_discussions=user_recent_discussions,
        saved_discussions=saved_discussions,

        # Community
        recent_activity=recent_activity,
        community_members=community_members,
        community_discussions=community_discussions
    )
@app.route("/create_post", methods=["GET", "POST"])
def create_post():

    if request.method == "POST":

        title = request.form["title"]
        content = request.form["content"]
        owner = session["user"]

        # Offensive Language Filter
        blocked_words = ["stupid", "idiot", "hate", "abuse"]

        for word in blocked_words:
            if word in title.lower() or word in content.lower():
                return "⚠ Offensive language detected. Discussion not allowed."

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create Discussion
        cursor.execute(
            "INSERT INTO discussions(title, content, owner) VALUES (?, ?, ?)",
            (title, content, owner)
        )

        # Activity Log
        cursor.execute(
            "INSERT INTO activity(activity) VALUES (?)",
            (f"{owner} created discussion: {title}",)
        )

        conn.commit()
        conn.close()

        return redirect("/view_posts")

    return render_template("create_post.html")
def get_user_badge(email, cursor):

    cursor.execute(
        "SELECT * FROM discussions WHERE owner=?",
        (email,)
    )

    user_posts = cursor.fetchall()

    total_likes = sum(post[4] for post in user_posts)

    total_comments = 0

    for post in user_posts:
        cursor.execute(
            "SELECT COUNT(*) FROM comments WHERE discussion_id=?",
            (post[0],)
        )
        total_comments += cursor.fetchone()[0]

    post_count = len(user_posts)

    reputation = (post_count * 10) + (total_likes * 2) + (total_comments * 5)

    if reputation < 50:
        return "Beginner"
    elif reputation < 100:
        return "Contributor"
    else:
        return "Expert"


@app.route("/view_posts")
def view_posts():

    search = request.args.get("search", "")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ==================================================
    # LOAD DISCUSSIONS
    # ==================================================

    if search:

        cursor.execute(
            """
            SELECT *
            FROM discussions
            WHERE title LIKE ?
            """,
            ('%' + search + '%',)
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM discussions
            """
        )

    posts = cursor.fetchall()


    # ==================================================
    # AUTHOR BADGES
    # ==================================================

    author_badges = {}

    for post in posts:

        owner = post[3]

        if owner not in author_badges:

            author_badges[owner] = get_user_badge(
                owner,
                cursor
            )


    # ==================================================
    # SAVED DISCUSSIONS
    # ==================================================

    saved_ids = []


    # ==================================================
    # LIKED DISCUSSIONS
    # ==================================================

    liked_ids = []


    if "user" in session:

        user = session["user"]


        # ------------------------------
        # Get saved discussions
        # ------------------------------

        cursor.execute(
            """
            SELECT discussion_id
            FROM bookmarks
            WHERE user_email = ?
            """,
            (user,)
        )

        saved_ids = [
            row[0]
            for row in cursor.fetchall()
        ]


        # ------------------------------
        # Get liked discussions
        # ------------------------------

        cursor.execute(
            """
            SELECT discussion_id
            FROM likes
            WHERE user_email = ?
            """,
            (user,)
        )

        liked_ids = [
            row[0]
            for row in cursor.fetchall()
        ]


    conn.close()


    # ==================================================
    # SEND DATA TO VIEW_POSTS.HTML
    # ==================================================

    return render_template(
        "view_posts.html",
        posts=posts,
        current_user=session.get("user"),
        author_badges=author_badges,
        saved_ids=saved_ids,
        liked_ids=liked_ids
    )
@app.route("/search_suggestions")
def search_suggestions():

    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title
        FROM discussions
        WHERE LOWER(title) LIKE LOWER(?)
        ORDER BY title
        LIMIT 6
        """,
        (f"%{query}%",)
    )

    results = cursor.fetchall()

    conn.close()

    suggestions = [
        {
            "id": row[0],
            "title": row[1]
        }
        for row in results
    ]

    return jsonify(suggestions)
@app.route("/comment", methods=["GET", "POST"])
def comment():

    if request.method == "POST":

        discussion_id = request.form["discussion_id"]
        comment_text = request.form["comment"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO comments(discussion_id, comment) VALUES (?, ?)",
            (discussion_id, comment_text)
        )

        conn.commit()
        conn.close()

        return "Comment Added Successfully!"

    return render_template("comment.html")
@app.route("/discussion/<int:discussion_id>", methods=["GET", "POST"])
def discussion(discussion_id):

    if "user" not in session:
        return redirect("/login")

    # ==================================================
    # ADD NEW COMMENT / REPLY
    # ==================================================

    if request.method == "POST":

        comment = request.form["comment"].strip()

        parent_comment_id = request.form.get("parent_comment_id")

        if parent_comment_id == "":
            parent_comment_id = None

        if comment:

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO comments
                (discussion_id, comment, author, parent_comment_id)
                VALUES (?, ?, ?, ?)
                """,
                (
                    discussion_id,
                    comment,
                    session["user"],
                    parent_comment_id
                )
            )

            cursor.execute(
                """
                SELECT title
                FROM discussions
                WHERE id=?
                """,
                (discussion_id,)
            )

            row = cursor.fetchone()

            title = row[0] if row else "Discussion"

            if parent_comment_id is None:
                activity = f"{session['user']} commented on: {title}"
            else:
                activity = f"{session['user']} replied to a comment on: {title}"

            cursor.execute(
                """
                INSERT INTO activity(activity)
                VALUES(?)
                """,
                (activity,)
            )

            conn.commit()
            conn.close()

        return redirect(f"/discussion/{discussion_id}#conversation")

    # ==================================================
    # LOAD DISCUSSION
    # ==================================================

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM discussions
        WHERE id=?
        """,
        (discussion_id,)
    )

    post = cursor.fetchone()

    # ==================================================
# LOAD PARENT COMMENTS WITH ACTUAL USER NAME
# ==================================================

    cursor.execute(
    """
    SELECT
        comments.id,
        comments.discussion_id,
        comments.comment,
        COALESCE(users.name, 'Community Member') AS author_name,
        comments.parent_comment_id

    FROM comments

    LEFT JOIN users
        ON comments.author = users.email

    WHERE comments.discussion_id = ?
      AND comments.parent_comment_id IS NULL

    ORDER BY comments.id ASC
    """,
    (discussion_id,)
    )

    comments = cursor.fetchall()

    # ==================================================
    # LOAD REPLIES
    # ==================================================
    cursor.execute(
    """
    SELECT
        comments.id,
        comments.discussion_id,
        comments.comment,
        COALESCE(users.name,'Community Member') AS author_name,
        comments.parent_comment_id,
        comments.author

    FROM comments

    LEFT JOIN users
        ON comments.author = users.email

    WHERE comments.discussion_id = ?
      AND comments.parent_comment_id IS NOT NULL

    ORDER BY comments.id ASC
    """,
    (discussion_id,)
    )

    replies = cursor.fetchall()

    print("REPLIES:", replies)
    # ==================================================
    # GET VOTE COUNTS
    # ==================================================

    cursor.execute(
        """
        SELECT
            comment_id,

            SUM(
                CASE
                    WHEN vote=1 THEN 1
                    ELSE 0
                END
            ),

            SUM(
                CASE
                    WHEN vote=-1 THEN 1
                    ELSE 0
                END
            )

        FROM comment_votes

        GROUP BY comment_id
        """
    )

    vote_rows = cursor.fetchall()

    comment_votes = {
        row[0]: {
            "upvotes": row[1] or 0,
            "downvotes": row[2] or 0
        }
        for row in vote_rows
    }

    # ==================================================
    # GET CURRENT USER VOTES
    # ==================================================

    cursor.execute(
        """
        SELECT comment_id, vote
        FROM comment_votes
        WHERE user=?
        """,
        (session["user"],)
    )

    user_vote_rows = cursor.fetchall()

    user_votes = {
        row[0]: row[1]
        for row in user_vote_rows
    }
    print("COMMENTS:", comments)
    print("REPLIES:", replies)
    conn.close()

    # ==================================================
    # SEND TO HTML
    # ==================================================

    return render_template(
        "discussion.html",
        post=post,
        comments=comments,
        replies=replies,
        current_user=session["user"],
        comment_votes=comment_votes,
        user_votes=user_votes
    )
# ==================================================
# DOWNLOAD DISCUSSION COMMENTS
# ==================================================

@app.route("/discussion/<int:discussion_id>/download_comments")
def download_comments(discussion_id):

    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get discussion
    cursor.execute(
        """
        SELECT title, content, owner
        FROM discussions
        WHERE id=?
        """,
        (discussion_id,)
    )

    post = cursor.fetchone()

    if not post:
        conn.close()
        return "Discussion not found.", 404

    # Get all comments and replies
    cursor.execute(
        """
        SELECT
            comments.comment,
            COALESCE(users.name, 'Community Member') AS author_name,
            comments.parent_comment_id
        FROM comments

        LEFT JOIN users
            ON comments.author = users.email

        WHERE comments.discussion_id=?

        ORDER BY comments.id ASC
        """,
        (discussion_id,)
    )

    all_comments = cursor.fetchall()

    conn.close()

    # Create downloadable text
    download_text = ""

    download_text += "=" * 60 + "\n"
    download_text += "K-DISC COMMUNITY DISCUSSION\n"
    download_text += "=" * 60 + "\n\n"

    download_text += f"Title: {post[0]}\n"
    download_text += f"Author: {post[2]}\n\n"

    download_text += "DISCUSSION\n"
    download_text += "-" * 60 + "\n"
    download_text += f"{post[1]}\n\n"

    download_text += "COMMENTS\n"
    download_text += "-" * 60 + "\n\n"

    if all_comments:

        for index, comment in enumerate(all_comments, start=1):

            comment_text = comment[0]
            author_name = comment[1]
            parent_id = comment[2]

            if parent_id is None:

                download_text += f"{index}. {author_name}\n"
                download_text += f"   {comment_text}\n\n"

            else:

                download_text += f"   ↳ Reply by {author_name}\n"
                download_text += f"     {comment_text}\n\n"

    else:

        download_text += "No comments available.\n"

    download_text += "\n"
    download_text += "=" * 60 + "\n"
    download_text += "Downloaded from K-DISC Community Platform\n"
    download_text += "=" * 60 + "\n"

    from flask import Response

    return Response(
        download_text,
        mimetype="text/plain",
        headers={
            "Content-Disposition":
                f'attachment; filename="discussion_{discussion_id}_comments.txt"'
        }
    )
# ==================================================
# COMMENT UPVOTE / DOWNVOTE - NO PAGE RELOAD
# ==================================================

@app.route("/comment_vote/<int:comment_id>/<vote>", methods=["POST"])
def comment_vote(comment_id, vote):

    try:
        vote = int(vote)
    except ValueError:
        return {
            "success": False,
            "message": "Invalid vote"
        }, 400

    # User must be logged in
    if "user" not in session:
        return {
            "success": False,
            "message": "Login required"
        }, 401

    # Only +1 and -1 allowed
    if vote not in (1, -1):
        return {
            "success": False,
            "message": "Invalid vote"
        }, 400

    user = session["user"]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ==================================================
    # CHECK COMMENT EXISTS
    # ==================================================

    cursor.execute(
        """
        SELECT id
        FROM comments
        WHERE id = ?
        """,
        (comment_id,)
    )

    comment = cursor.fetchone()

    if comment is None:
        conn.close()

        return {
            "success": False,
            "message": "Comment not found"
        }, 404

    # ==================================================
    # CHECK EXISTING USER VOTE
    # ==================================================

    cursor.execute(
        """
        SELECT vote
        FROM comment_votes
        WHERE comment_id = ?
          AND user = ?
        """,
        (comment_id, user)
    )

    existing_vote = cursor.fetchone()

    # Debug
    print("================================")
    print("COMMENT ID:", comment_id)
    print("CLICKED VOTE:", vote)
    print("USER:", user)
    print("EXISTING VOTE:", existing_vote)
    print("================================")

    # ==================================================
    # HANDLE EXISTING VOTE
    # ==================================================

    if existing_vote:

        old_vote = existing_vote[0]

        # ----------------------------------------------
        # SAME VOTE CLICKED AGAIN
        # Example:
        # 👍 → 👍
        # Remove vote
        # ----------------------------------------------

        if old_vote == vote:

            cursor.execute(
                """
                DELETE FROM comment_votes
                WHERE comment_id = ?
                  AND user = ?
                """,
                (comment_id, user)
            )

            current_user_vote = 0

            print("SAME VOTE CLICKED - VOTE REMOVED")

        # ----------------------------------------------
        # CHANGE VOTE
        # Example:
        # 👍 → 👎
        # OR
        # 👎 → 👍
        # ----------------------------------------------

        else:

            print("CHANGING VOTE")
            print("OLD VOTE:", old_vote)
            print("NEW VOTE:", vote)

            cursor.execute(
                """
                UPDATE comment_votes
                SET vote = ?
                WHERE comment_id = ?
                  AND user = ?
                """,
                (
                    vote,
                    comment_id,
                    user
                )
            )

            current_user_vote = vote

    # ==================================================
    # FIRST VOTE
    # ==================================================

    else:

        cursor.execute(
            """
            INSERT INTO comment_votes
            (comment_id, user, vote)
            VALUES (?, ?, ?)
            """,
            (
                comment_id,
                user,
                vote
            )
        )

        current_user_vote = vote

        print("FIRST VOTE ADDED:", vote)

    # ==================================================
    # SAVE DATABASE CHANGES
    # ==================================================

    conn.commit()

    # ==================================================
    # GET UPDATED VOTE COUNTS
    # ==================================================

    cursor.execute(
        """
        SELECT

            SUM(
                CASE
                    WHEN vote = 1 THEN 1
                    ELSE 0
                END
            ) AS upvotes,

            SUM(
                CASE
                    WHEN vote = -1 THEN 1
                    ELSE 0
                END
            ) AS downvotes

        FROM comment_votes

        WHERE comment_id = ?
        """,
        (comment_id,)
    )

    counts = cursor.fetchone()

    upvotes = counts[0] or 0
    downvotes = counts[1] or 0

    print("UPDATED UPVOTES:", upvotes)
    print("UPDATED DOWNVOTES:", downvotes)
    print("CURRENT USER VOTE:", current_user_vote)

    conn.close()

    # ==================================================
    # RETURN JSON TO JAVASCRIPT
    # NO PAGE RELOAD
    # ==================================================

    return {
        "success": True,
        "comment_id": comment_id,
        "upvotes": upvotes,
        "downvotes": downvotes,
        "user_vote": current_user_vote
    }

    # ==================================================
    # RETURN DATA TO JAVASCRIPT
    # NO REDIRECT = NO PAGE RELOAD
    # ==================================================

    return {
        "success": True,
        "comment_id": comment_id,
        "upvotes": upvotes,
        "downvotes": downvotes,
        "user_vote": current_user_vote
    }
@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect(url_for("login"))
@app.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM discussions WHERE id=?",
        (post_id,)
    )

    post = cursor.fetchone()

    # Security Check
    if post[3] != session.get("user"):
        conn.close()
        return "Access Denied"

    if request.method == "POST":

        title = request.form["title"]
        content = request.form["content"]

        cursor.execute(
            "UPDATE discussions SET title=?, content=? WHERE id=?",
            (title, content, post_id)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("view_posts"))

    conn.close()

    return render_template(
        "edit_post.html",
        post=post
    )
@app.route("/delete_post/<int:post_id>")
def delete_post(post_id):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM discussions WHERE id=?",
        (post_id,)
    )

    post = cursor.fetchone()

    # Security Check
    if post[3] != session.get("user"):
        conn.close()
        return "Access Denied"

    cursor.execute(
        "DELETE FROM discussions WHERE id=?",
        (post_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("view_posts"))
@app.route("/summary/<int:post_id>")
def summary(post_id):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM discussions WHERE id=?",
        (post_id,)
    )

    post = cursor.fetchone()

    conn.close()

    content = post[2]

    # Simple AI Summary (first version)
    words = content.split()

    if len(words) > 10:
        summary_text = "Summary: " + " ".join(words[:10]) + "..."
    else:
        summary_text = "Summary: " + content

    return render_template(
        "summary.html",
        content=content,
        summary=summary_text
    )
@app.route("/sentiment/<int:post_id>")
def sentiment(post_id):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM discussions WHERE id=?",
        (post_id,)
    )

    post = cursor.fetchone()

    conn.close()

    content = post[2].lower()

    positive_words = ["good", "great", "love", "excellent", "amazing"]
    negative_words = ["bad", "hate", "poor", "terrible", "awful"]

    score = 0

    for word in positive_words:
        if word in content:
            score += 1

    for word in negative_words:
        if word in content:
            score -= 1

    if score > 0:
        result = "Positive"
        sentiment_type = "positive"
    elif score < 0:
        result = "Negative"
        sentiment_type = "negative"
    else:
        result = "Neutral"
        sentiment_type = "neutral"

    return render_template(
        "sentiment.html",
        content=post[2],
        title=post[1],
        result=result,
        sentiment_type=sentiment_type
    )
@app.route("/analytics")
def analytics():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM discussions")
    total_discussions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM comments")
    total_comments = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "analytics.html",
        total_users=total_users,
        total_discussions=total_discussions,
        total_comments=total_comments
    )
@app.route("/profile")
def profile():

    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM discussions WHERE owner=?",
        (session["user"],)
    )

    my_posts = cursor.fetchall()

    # Total Likes Received
    total_likes = 0

    for post in my_posts:
        total_likes += post[4]

    # Total Comments Received
    total_comments = 0

    for post in my_posts:

        cursor.execute(
            "SELECT COUNT(*) FROM comments WHERE discussion_id=?",
            (post[0],)
        )

        total_comments += cursor.fetchone()[0]

    # Reputation Calculation
    post_count = len(my_posts)

    reputation = (
        post_count * 10
        + total_likes * 2
        + total_comments * 5
    )

    # Badge System
    if reputation < 50:
        badge = "🥉 Beginner"

    elif reputation < 100:
        badge = "🥈 Contributor"

    else:
        badge = "🥇 Expert"

    # Saved Discussions
    cursor.execute(
        """
        SELECT discussions.*
        FROM discussions

        JOIN bookmarks
        ON discussions.id = bookmarks.discussion_id

        WHERE bookmarks.user_email=?
        """,
        (session["user"],)
    )

    saved_posts = cursor.fetchall()

    conn.close()

    return render_template(
        "profile.html",
        email=session["user"],
        posts=my_posts,
        badge=badge,
        total_likes=total_likes,
        total_comments=total_comments,
        reputation=reputation,
        saved_posts=saved_posts
    )
# ==================================================
# LIKE / UNLIKE DISCUSSION - NO PAGE RELOAD
# ==================================================

@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):

    # User must be logged in
    if "user" not in session:
        return {
            "success": False,
            "message": "Login required"
        }, 401

    user = session["user"]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ==================================================
    # CHECK DISCUSSION EXISTS
    # ==================================================

    cursor.execute(
        """
        SELECT title
        FROM discussions
        WHERE id = ?
        """,
        (post_id,)
    )

    post = cursor.fetchone()

    if post is None:

        conn.close()

        return {
            "success": False,
            "message": "Discussion not found"
        }, 404

    title = post[0]

    # ==================================================
    # CHECK WHETHER USER ALREADY LIKED
    # ==================================================

    cursor.execute(
        """
        SELECT *
        FROM likes
        WHERE user_email = ?
        AND discussion_id = ?
        """,
        (user, post_id)
    )

    existing_like = cursor.fetchone()

    # ==================================================
    # IF ALREADY LIKED -> UNLIKE
    # ==================================================

    if existing_like:

        cursor.execute(
            """
            DELETE FROM likes
            WHERE user_email = ?
            AND discussion_id = ?
            """,
            (user, post_id)
        )

        # Decrease like count
        # CASE prevents negative values
        cursor.execute(
            """
            UPDATE discussions

            SET likes =
                CASE
                    WHEN likes > 0
                    THEN likes - 1
                    ELSE 0
                END

            WHERE id = ?
            """,
            (post_id,)
        )

        liked = False

    # ==================================================
    # IF NOT LIKED -> ADD LIKE
    # ==================================================

    else:

        cursor.execute(
            """
            INSERT INTO likes
            (user_email, discussion_id)

            VALUES (?, ?)
            """,
            (user, post_id)
        )

        # Increase like count
        cursor.execute(
            """
            UPDATE discussions

            SET likes = likes + 1

            WHERE id = ?
            """,
            (post_id,)
        )

        liked = True

        # Activity log only when liking
        cursor.execute(
            """
            INSERT INTO activity(activity)
            VALUES (?)
            """,
            (
                f"{user} liked: {title}",
            )
        )

    # ==================================================
    # SAVE CHANGES
    # ==================================================

    conn.commit()

    # ==================================================
    # GET UPDATED LIKE COUNT
    # ==================================================

    cursor.execute(
        """
        SELECT likes
        FROM discussions
        WHERE id = ?
        """,
        (post_id,)
    )

    result = cursor.fetchone()

    likes = result[0] if result else 0

    conn.close()

    # ==================================================
    # RETURN JSON TO JAVASCRIPT
    # ==================================================

    return {
        "success": True,
        "liked": liked,
        "likes": likes
    }
@app.route("/top_posts")
def top_posts():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM discussions ORDER BY likes DESC"
    )

    posts = cursor.fetchall()

    conn.close()

    return render_template(
        "top_posts.html",
        posts=posts
    )
@app.route("/recommend/<int:post_id>")
def recommend(post_id):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM discussions")
    all_posts = cursor.fetchall()

    conn.close()

    current_post = next((p for p in all_posts if p[0] == post_id), None)

    texts = [p[1] + " " + p[2] for p in all_posts]  # title + content
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(texts)

    current_index = [p[0] for p in all_posts].index(post_id)
    similarities = cosine_similarity(tfidf_matrix[current_index], tfidf_matrix).flatten()

    ranked = sorted(
        [(all_posts[i], score) for i, score in enumerate(similarities) if all_posts[i][0] != post_id],
        key=lambda x: x[1],
        reverse=True
    )

    recommendations = [r[0] for r in ranked[:5]]

    return render_template("recommend.html", post=current_post, recommendations=recommendations)
@app.route("/admin")
def admin():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total Users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Total Discussions
    cursor.execute("SELECT COUNT(*) FROM discussions")
    total_discussions = cursor.fetchone()[0]

    # Total Comments
    cursor.execute("SELECT COUNT(*) FROM comments")
    total_comments = cursor.fetchone()[0]

    # Total Likes
    cursor.execute("SELECT SUM(likes) FROM discussions")
    total_likes = cursor.fetchone()[0]

    # Most Liked Discussion
    cursor.execute(
        "SELECT title, likes FROM discussions ORDER BY likes DESC LIMIT 1"
    )
    top_post = cursor.fetchone()

    # Most Active User
    cursor.execute(
        """
        SELECT owner, COUNT(*)
        FROM discussions
        GROUP BY owner
        ORDER BY COUNT(*) DESC
        LIMIT 1
        """
    )
    most_active_user = cursor.fetchone()

    # Most Commented Discussion
    cursor.execute(
        """
        SELECT discussions.title,
               COUNT(comments.id) as comment_count

        FROM discussions

        LEFT JOIN comments
        ON discussions.id = comments.discussion_id

        GROUP BY discussions.id

        ORDER BY comment_count DESC

        LIMIT 1
        """
    )
    most_commented = cursor.fetchone()

    # Chart Data
    cursor.execute(
        "SELECT title, likes FROM discussions"
    )

    chart_data = cursor.fetchall()

    labels = []
    likes = []

    for row in chart_data:
        labels.append(row[0])
        likes.append(row[1])

    conn.close()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_discussions=total_discussions,
        total_comments=total_comments,
        total_likes=total_likes,
        top_post=top_post,
        most_active_user=most_active_user,
        most_commented=most_commented,
        labels=labels,
        likes=likes
    )
@app.route("/trending")
def trending():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, likes
        FROM discussions
        ORDER BY likes DESC
        """
    )

    posts = cursor.fetchall()

    conn.close()

    return render_template(
        "trending.html",
        posts=posts
    )
@app.route("/category_analysis")
def category_analysis():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM discussions")

    posts = cursor.fetchall()

    conn.close()

    categorized_posts = []

    for post in posts:

        title = post[1].lower()

        if "python" in title:
            category = "Programming"

        elif "ai" in title or "machine learning" in title:
            category = "Artificial Intelligence"

        elif "flask" in title:
            category = "Web Development"

        elif "sql" in title or "database" in title:
            category = "Database"

        else:
            category = "General"

        categorized_posts.append(
            (post[1], category)
        )

    return render_template(
        "category_analysis.html",
        posts=categorized_posts
    )
@app.route("/solve/<int:post_id>")
def solve(post_id):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE discussions SET status='Solved' WHERE id=?",
        (post_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("view_posts"))
@app.route("/bookmark/<int:post_id>")
def bookmark(post_id):

    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM bookmarks
        WHERE user_email=? AND discussion_id=?
        """,
        (session["user"], post_id)
    )

    existing_bookmark = cursor.fetchone()

    if existing_bookmark:
        conn.close()
        return "Discussion already saved."

    cursor.execute(
        """
        INSERT INTO bookmarks(user_email, discussion_id)
        VALUES (?, ?)
        """,
        (session["user"], post_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("view_posts"))
@app.route("/bookmarks")
def bookmarks():

    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            d.id,
            d.title,
            d.content,
            d.owner,
            d.likes,
            d.status
        FROM bookmarks AS b
        JOIN discussions AS d
            ON d.id = b.discussion_id
        WHERE LOWER(b.user_email) = LOWER(?)
        ORDER BY b.id DESC
        """,
        (session["user"],)
    )

    saved_posts = cursor.fetchall()

    conn.close()

    return render_template(
        "bookmarks.html",
        saved_posts=saved_posts
    )


@app.route("/activity")
def activity():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM activity ORDER BY id DESC"
    )

    activities = cursor.fetchall()

    conn.close()

    return render_template(
        "activity.html",
        activities=activities
    )
@app.route("/discourse_topics")
def discourse_topics():

    topics = get_latest_topics()

    topic_discussions = []

    for topic in topics:

        discussion = get_topic_discussion(topic["id"])

        topic_discussions.append({
            "id": topic["id"],
            "title": topic["title"],
            "created_at": topic["created_at"],
            "views": topic.get("views", 0),
            "reply_count": topic.get("reply_count", 0),
            "comments": discussion["comments"]
        })

    return render_template(
        "discourse_topics.html",
        topics=topic_discussions
    )
@app.route("/unbookmark/<int:post_id>")
def unbookmark(post_id):

    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM bookmarks WHERE user_email=? AND discussion_id=?",
        (session["user"], post_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("view_posts"))
import json

@app.route("/discourse_summary")
def discourse_summary():
    from gemini_helper import summarize_discussion
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topic_summaries (
            topic_id INTEGER PRIMARY KEY,
            title TEXT,
            summary TEXT,
            topic_date TEXT,
            url TEXT,
            views INTEGER,
            replies INTEGER,
            comments_json TEXT
        )
    """)

    topics = get_latest_topics()

    for topic in topics:

        topic_id = topic["id"]

        cursor.execute("SELECT * FROM topic_summaries WHERE topic_id=?", (topic_id,))
        existing = cursor.fetchone()

        if existing:
            continue

        discussion = get_topic_discussion(topic_id)

        comment_texts = [c["text"] for c in discussion["comments"]]
        
        summary_text = summarize_discussion(discussion["title"], comment_texts)

        
        cursor.execute(
            """INSERT INTO topic_summaries
               (topic_id, title, summary, topic_date, url, views, replies, comments_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                topic_id,
                discussion["title"],
                summary_text,
                discussion["created_at"],
                discussion["url"],
                discussion["views"],
                discussion["replies"],
                json.dumps(discussion["comments"][:5])
            )
        )

        conn.commit()

    cursor.execute("SELECT * FROM topic_summaries ORDER BY topic_date DESC")
    rows = cursor.fetchall()

    conn.close()

    summaries = []

    for row in rows:
        summaries.append({
            "topic_id": row[0],
            "title": row[1],
            "summary": row[2],
            "date": row[3],
            "url": row[4],
            "views": row[5],
            "replies": row[6],
            "comments": json.loads(row[7])
        })

    return render_template("discourse_summary.html", summaries=summaries)
@app.route("/delete_reply/<int:reply_id>")
def delete_reply(reply_id):

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT discussion_id, author
        FROM comments
        WHERE id=?
        """,
        (reply_id,)
    )

    row = cursor.fetchone()

    if row is None:
        conn.close()
        return redirect("/view_posts")

    discussion_id = row[0]
    author = row[1]

    # Only reply owner can delete
    if author != session["user"]:
        conn.close()
        return "Access Denied"

    cursor.execute(
        """
        DELETE FROM comments
        WHERE id=?
        """,
        (reply_id,)
    )

    conn.commit()
    conn.close()

    return redirect(f"/discussion/{discussion_id}")

# ==================================================
# ADMIN DASHBOARD
# ==================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    # ----------------------------------------------
    # CHECK LOGIN
    # ----------------------------------------------

    if "user" not in session:
        return redirect(url_for("login"))


    # ----------------------------------------------
    # CONNECT DATABASE
    # ----------------------------------------------

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()


    # ----------------------------------------------
    # GET CURRENT USER
    # ----------------------------------------------

    cursor.execute(
        """
        SELECT id, name, email, role, user_id
        FROM users
        WHERE LOWER(email) = ?
        """,
        (session["user"].lower(),)
    )

    current_user = cursor.fetchone()


    # ----------------------------------------------
    # USER DOES NOT EXIST
    # ----------------------------------------------

    if current_user is None:

        conn.close()

        session.clear()

        return redirect(url_for("login"))


    # ----------------------------------------------
    # ADMIN SECURITY CHECK
    # ----------------------------------------------

    if current_user["role"] != "admin":

        conn.close()

        return redirect(url_for("home"))


    # ----------------------------------------------
    # TOTAL USERS
    # ----------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        """
    )

    total_users = cursor.fetchone()[0]


    # ----------------------------------------------
    # TOTAL DISCUSSIONS
    # ----------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM discussions
        """
    )

    total_discussions = cursor.fetchone()[0]


    # ----------------------------------------------
    # TOTAL COMMENTS
    # ----------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM comments
        """
    )

    total_comments = cursor.fetchone()[0]


    # ----------------------------------------------
    # TOTAL LIKES
    # ----------------------------------------------

    cursor.execute(
        """
        SELECT COALESCE(SUM(likes), 0)
        FROM discussions
        """
    )

    total_likes = cursor.fetchone()[0]


    # ----------------------------------------------
    # RECENT USERS
    # ----------------------------------------------

    cursor.execute(
        """
        SELECT
            id,
            name,
            email,
            role,
            user_id
        FROM users
        ORDER BY id DESC
        LIMIT 5
        """
    )

    recent_users = cursor.fetchall()


    # ----------------------------------------------
    # RECENT DISCUSSIONS
    # ----------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM discussions
        ORDER BY id DESC
        LIMIT 5
        """
    )

    recent_discussions = cursor.fetchall()


    # ----------------------------------------------
    # CLOSE DATABASE
    # ----------------------------------------------

    conn.close()


    # ----------------------------------------------
    # OPEN ADMIN DASHBOARD
    # ----------------------------------------------

    return render_template(
        "admin_dashboard.html",

        current_user=current_user,

        total_users=total_users,
        total_discussions=total_discussions,
        total_comments=total_comments,
        total_likes=total_likes,

        recent_users=recent_users,
        recent_discussions=recent_discussions
    )

if __name__ == "__main__":
    app.run(debug=True)


