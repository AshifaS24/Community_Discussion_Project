# from curses import flash
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from discourse_api import get_latest_topics, get_topic_discussion
import sqlite3
from flask import Flask, render_template, request, redirect, session, jsonify, flash,url_for
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "community.db"
app = Flask(__name__)
app.secret_key = "mysecretkey"

@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users(name,email,password) VALUES(?,?,?)",
            (name, email, password)
        )

        conn.commit()
        conn.close()

        return render_template("register_success.html")

    return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:
            session["user"] = email
            return redirect(url_for("dashboard"))

        return "Invalid Email or Password"

    return render_template("login.html")
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

    if search:
        cursor.execute(
            "SELECT * FROM discussions WHERE title LIKE ?",
            ('%' + search + '%',)
        )
    else:
        cursor.execute("SELECT * FROM discussions")

    posts = cursor.fetchall()

    author_badges = {}

    for post in posts:
        owner = post[3]
        if owner not in author_badges:
            author_badges[owner] = get_user_badge(owner, cursor)

    saved_ids = []

    if "user" in session:
        cursor.execute(
            "SELECT discussion_id FROM bookmarks WHERE user_email=?",
            (session["user"],)
        )
        saved_ids = [row[0] for row in cursor.fetchall()]

    conn.close()

    return render_template(
        "view_posts.html",
        posts=posts,
        current_user=session.get("user"),
        author_badges=author_badges,
        saved_ids=saved_ids
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

    # None = Normal comment
    # Otherwise = Reply to another comment
    parent_comment_id = request.form.get("parent_comment_id")

    if parent_comment_id == "":
        parent_comment_id = None

    if comment:

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Save comment or reply
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

        # Get discussion title
        cursor.execute(
            """
            SELECT title
            FROM discussions
            WHERE id = ?
            """,
            (discussion_id,)
        )

        result = cursor.fetchone()

        if result:
            title = result[0]
        else:
            title = "Discussion"

        # Save activity
        if parent_comment_id is None:
            activity_text = (
                f"{session['user']} commented on: {title}"
            )
        else:
            activity_text = (
                f"{session['user']} replied to a comment on: {title}"
            )

        cursor.execute(
            """
            INSERT INTO activity(activity)
            VALUES (?)
            """,
            (activity_text,)
        )

        conn.commit()
        conn.close()

    # Return to discussion page (runs whether comment was saved or not)
    return redirect(
        f"/discussion/{discussion_id}#conversation"
    )

    # ==================================================
    # LOAD DISCUSSION
    # ==================================================

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()


    # Get discussion
    cursor.execute(
        """
        SELECT *
        FROM discussions
        WHERE id = ?
        """,
        (discussion_id,)
    )

    post = cursor.fetchone()


  # Get comments with registered user name
    cursor.execute(
    """
    SELECT
        comments.id,
        comments.discussion_id,
        comments.comment,
        COALESCE(users.name, 'Community Member') AS author_name
    FROM comments
    LEFT JOIN users
        ON comments.author = users.email
    WHERE comments.discussion_id = ?
    ORDER BY comments.id ASC
    """,
    (discussion_id,)
)

    comments = cursor.fetchall()


    # ==================================================
    # GET VOTE COUNTS
    # ==================================================
# 1. GET DISCUSSION
    cursor.execute(
    """
    SELECT *
    FROM discussions
    WHERE id = ?
    """,
    (discussion_id,)
)

    post = cursor.fetchone()


# 2. GET COMMENTS WITH REGISTERED NAME
    cursor.execute(
    """
    SELECT
        comments.id,
        comments.discussion_id,
        comments.comment,
        COALESCE(users.name, 'Community Member') AS author_name
    FROM comments
    LEFT JOIN users
        ON comments.author = users.email
    WHERE comments.discussion_id = ?
    ORDER BY comments.id ASC
    """,
    (discussion_id,)
)

    comments = cursor.fetchall()

# 3. GET VOTE COUNTS
    cursor.execute(
    """
    SELECT
        comment_id,

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

    GROUP BY comment_id
    """
    )

    vote_rows = cursor.fetchall()


    comment_votes = {
        row[0]: {
            "upvotes": row[1],
            "downvotes": row[2]
        }
        for row in vote_rows
    }

    print("DEBUG comment_votes:", comment_votes)

    # ==================================================
    # GET CURRENT USER'S VOTES
    # ==================================================

    cursor.execute(
        """
        SELECT comment_id, vote
        FROM comment_votes
        WHERE user = ?
        """,
        (session["user"],)
    )

    user_vote_rows = cursor.fetchall()


    user_votes = {
        row[0]: row[1]
        for row in user_vote_rows
    }
    print("DEBUG comment_votes:", comment_votes)
    print("DEBUG user_votes:", user_votes)

    conn.close()


    # ==================================================
    # SEND DATA TO HTML
    # ==================================================

    return render_template(
        "discussion.html",
        post=post,
        comments=comments,
        current_user=session["user"],
        comment_votes=comment_votes,
        user_votes=user_votes
    )
@app.route("/comment_vote/<int:comment_id>/<vote>")
def comment_vote(comment_id, vote):

    vote = int(vote)
    print("====== COMMENT VOTE ROUTE CALLED ======")
    print("Comment ID:", comment_id)
    print("Vote:", vote)

    if "user" not in session:
        return redirect(url_for("login"))

    if vote not in (1, -1):
        return redirect(url_for("view_posts"))

    user = session["user"]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()


    # Get discussion ID for redirect
    cursor.execute(
        """
        SELECT discussion_id
        FROM comments
        WHERE id = ?
        """,
        (comment_id,)
    )

    result = cursor.fetchone()

    if not result:
        conn.close()
        return redirect(url_for("view_posts"))

    discussion_id = result[0]


    # Check existing vote
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


    if existing_vote:
        old_vote = existing_vote[0]
        if old_vote == vote:

            # Same vote clicked again → remove vote
            cursor.execute(
                """
                DELETE FROM comment_votes
                WHERE comment_id = ?
                AND user = ?
                """,
                (comment_id, user)
            )

        else:
            # Change upvote ↔ downvote
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

    else:

        # First vote
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


    conn.commit()
    conn.close()


    return redirect(
        f"/discussion/{discussion_id}#comment-{comment_id}"
    )
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
@app.route("/like/<int:post_id>")
def like_post(post_id):

    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM likes WHERE user_email=? AND discussion_id=?",
        (session["user"], post_id)
    )

    existing_like = cursor.fetchone()

    if existing_like:
        conn.close()
        flash("You already liked this discussion.", "info")
        return redirect(request.referrer or "/view_posts")

    # Save Like Record
    cursor.execute(
        "INSERT INTO likes(user_email, discussion_id) VALUES (?, ?)",
        (session["user"], post_id)
    )

    # Increase Like Count
    cursor.execute(
        "UPDATE discussions SET likes = likes + 1 WHERE id=?",
        (post_id,)
    )

    # Get Discussion Title
    cursor.execute(
        "SELECT title FROM discussions WHERE id=?",
        (post_id,)
    )

    title = cursor.fetchone()[0]

    # Activity Log
    cursor.execute(
        "INSERT INTO activity(activity) VALUES (?)",
        (f"{session['user']} liked: {title}",)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("view_posts"))
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


if __name__ == "__main__":
    app.run(debug=True)


