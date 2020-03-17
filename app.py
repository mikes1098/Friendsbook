# Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import hashlib
public1 = 0
public2 = 0
# hexdigest() or digest() assumes we can change password in database from size 50 to 64.
# Otherwise we would slice [0:50], which may hash a few different passwords as the same
# which isn't optimal. Better to change varchar size to 64 (May have been mentioned in class)

# Initialize the app from Flask
app = Flask(__name__)

# Configure MySQL
conn = pymysql.connect(host='localhost',
                       port=8889,
                       user='root',
                       password='root',
                       db='PriCoSha',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)


# Define a route to hello function
@app.route('/')
def hello():
    return render_template('index.html', posts=public())


# Define route for login
@app.route('/login')
def login():
    return render_template('login.html')


# Define route for register
@app.route('/register')
def register():
    return render_template('register.html')


# Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    # grabs information from the forms
    email = request.form['email']
    password = request.form['password'].encode('utf-8')
    hashedPass = hashlib.sha256()
    hashedPass.update(password)
    # cursor used to send queries
    cursor = conn.cursor()
    # executes query
    query = 'SELECT * FROM Person WHERE email = %s and password = %s'
    cursor.execute(query, (email, hashedPass.hexdigest()))
    # stores the results in a variable
    data = cursor.fetchone()
    # use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if (data):
        # creates a session for the the user
        # session is a built in
        session['email'] = email
        return redirect(url_for('home'))
    else:
        # returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)


# Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    # grabs information from the forms
    email = request.form['email']
    password = request.form['password'].encode('utf-8')
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    hashedPass = hashlib.sha256()
    hashedPass.update(password)
    # cursor used to send queries
    cursor = conn.cursor()
    # executes query
    query = 'SELECT * FROM Person WHERE email = %s'
    cursor.execute(query, (email))
    # stores the results in a variable
    data = cursor.fetchone()
    # use fetchall() if you are expecting more than 1 data row
    error = None
    if (data):
        # If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error=error)
    else:
        ins = 'INSERT INTO Person VALUES(%s,%s,%s,%s)'
        cursor.execute(ins, (email, hashedPass.hexdigest(), first_name, last_name))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/post', methods=['GET', 'POST'])
def post():
    email = session['email']
    cursor = conn.cursor();
    item_id = request.form['item_id']
    item_name = request.form['item_name']
    file_path = request.form['file_path']
    public = request.form['Privacy']
    global public1
    if (public == 'Yes'):
        public1 = 1
    if (public == 'No'):
        public1 = 0
    query = 'INSERT INTO contentitem (item_id, email_post, item_name, post_time, file_path, is_pub) VALUES(%s, %s, %s, NOW(), %s,%s)'
    cursor.execute(query, (item_id, email, item_name, file_path, public1))
    if (public1 == 0):
        fg_name = request.form['fg_name']
        ins = 'Insert into share (owner_email, fg_name, item_id) Values(%s, %s, %s)'
        cursor.execute(ins, (email, fg_name, item_id))
    query1 = 'Insert into relevant_data(item_id, item_length, no_of_tags) values (%s, %s, %s)'
    cursor.execute(query1, (item_id, len(item_name), 0))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))


@app.route('/public')
def public():
    cursor = conn.cursor();
    query = 'SELECT item_id, email_post, post_time, file_Path, item_Name FROM ContentItem WHERE (is_pub = 1) AND (post_time >= NOW() - INTERVAL 1 DAY) ORDER BY post_time DESC '
    cursor.execute(query)
    datas = cursor.fetchall()
    cursor.close()
    return datas


@app.route('/home')
def home():
    user = session['email']
    cursor = conn.cursor();
    query = 'SELECT item_id, email_post, post_time, file_Path, item_Name FROM ContentItem WHERE (email_post = %s OR is_pub=1) ORDER BY Post_time DESC '
    cursor.execute(query, (user))
    data = cursor.fetchall()
    cursor.close()
    return render_template('home.html', email=user, posts=data, Tags=showTags(), manageTags=manageTags())


@app.route('/logout')
def logout():
    session.pop('email')
    return redirect('/')


@app.route('/createTag', methods=['GET', 'POST'])
def createTag():
    user = session['email']
    status = 0
    tagged_person = request.form['Tagged']
    Item_ID = request.form['Item_id']
    cursor = conn.cursor();
    query = 'SELECT is_pub FROM contentItem WHERE item_id = %s AND email_post = %s'
    cursor.execute(query, (Item_ID, user))
    data = cursor.fetchone()
    if (tagged_person == user):
        status = 1
        cursor = conn.cursor();
        query = 'INSERT into Tag (email_tagged, email_tagger, item_id, status, tagtime) Values(%s,%s,%s,%s,NOW())'
        cursor.execute(query, (tagged_person, user, Item_ID, status))
        conn.commit()
        cursor.close()
        return redirect(url_for('home'))
    elif (data['is_pub'] == 1):
        cursor = conn.cursor();
        query = 'INSERT into Tag (email_tagged, email_tagger, item_id, status, tagtime) Values(%s,%s,%s,%s,NOW())'
        cursor.execute(query, (tagged_person, user, Item_ID, status))
        query1 = 'update relevant_data set no_of_tags = (%s+1) where relevant_data.item_id = %s '
        cursor.execute(query1, (Item_ID))

        conn.commit()
        cursor.close()
        return redirect(url_for('home'))
    else:
        error = 'Cannot create this tag'
        return render_template('show_posts.html', error=error)


@app.route('/showTags')
def showTags():
    user = session['email']
    cursor = conn.cursor()
    query = 'SELECT DISTINCT Tag.email_tagger, item_id, fname,lname FROM Person NATURAL JOIN Tag WHERE (status = 1 AND Tag.email_tagged = %s AND Tag.email_tagger = Person.email)'
    cursor.execute(query, (user))
    datas = cursor.fetchall()
    cursor.close()
    return datas


@app.route('/manageTags')
def manageTags():
    user = session['email']
    cursor = conn.cursor()
    query = 'SELECT item_id,email_tagger FROM Tag NATURAL JOIN ContentItem WHERE email_tagged=%s and status =0'
    cursor.execute(query, (user))
    datas = cursor.fetchall()
    cursor.close()
    return datas


@app.route('/updateTag', methods=['GET', 'POST'])
def updateTag():
    user = session['email']
    itemID = request.form['itemID']
    email = request.form['email']
    status = request.form['status']
    if (status == "one"):
        cursor = conn.cursor()
        query = "UPDATE Tag SET status=1 WHERE (email_tagger = %s AND item_id = %s AND email_tagged = %s)"
        cursor.execute(query, (email, itemID, user))
        conn.commit()
        cursor.close()
        return redirect(url_for('home'))
    elif (status == "two"):
        cursor = conn.cursor()
        query = "DELETE FROM Tag WHERE email_tagger = %s AND item_id = %s AND email_tagged = %s"
        cursor.execute(query, (email, itemID, user))
        conn.commit()
        cursor.close()
        return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))


@app.route('/wantToAddFriend')
def wantToFriend():
    return render_template('add.html')

@app.route('/addFriendValidation', methods=['GET', 'POST'])
def friendValidation():
    s_email = session['email']
    cursor = conn.cursor();
    fg_name = request.form['fg_name']
    f_email = request.form['email']
    query = 'SELECT email FROM Person WHERE email = %s and email not in (select email from belong where person.email = belong.email)'
    cursor.execute(query, (f_email))
    if query is not None:
        query1 = 'insert into belong (email, owner_email, fg_name) VALUES (%s, %s, %s)'
        cursor.execute(query1, (f_email, s_email, fg_name))

    conn.commit()
    cursor.close()
    return render_template('done.html')


@app.route('/more_datas')
def more_datas():
    return render_template('info.html')

@app.route('/Relevant_data', methods=['GET', 'POST'])
def Relevant():
    cursor = conn.cursor();
    id = request.form['item_id']
    query = 'SELECT item_length, no_of_tags from relevant_data where item_id = %s'
    cursor.execute(query, (id))
    data = cursor.fetchall()
    conn.commit()
    cursor.close()
    return render_template('data.html', value=data)


@app.route('/TowantTocomment')
def wantTocomment():
    return render_template('comm.html')

@app.route('/Towritecomments', methods=['GET', 'POST'])
def writecomments():
    cursor = conn.cursor();
    comm = request.form['comment']
    item = request.form['item_id']
    access = request.form['public']
    global public2
    if (access == 'Yes'):
          public2 = 1
    if (access == 'No'):
          public2 = 0
    query = 'insert into comments(comment, item_id, access) VALUES (%s, %s, %s)'
    cursor.execute(query, (comm, item, public2))
    conn.commit()
    cursor.close()
    return render_template('done.html')



app.secret_key = 'some key that you will never guess'
# Run the app on localhost port 5000
# debug = True -> you don't have to restart flask
# for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)


