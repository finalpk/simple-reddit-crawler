CREATE SCHEMA reddit DEFAULT CHARSET 'utf8mb4' COLLATE 'utf8mb4_general_ci';

USE reddit;

CREATE TABLE threads (
id int primary key not null auto_increment,
id_thread varchar(16) not null unique key,
sub text not null,
author text not null,
title text not null,
self text not null,
url varchar(255) not null,
permalink varchar(255) not null,
score int not null,
created timestamp null default null
) engine=innodb;

CREATE TABLE comments (
id int primary key not null auto_increment,
id_comment varchar(16) not null unique key,
id_thread int not null,
author text not null,
comment text not null,
url varchar(255) not null,
score int not null,
created timestamp null default null
) engine=innodb;

CREATE TABLE logs (
id int primary key not null auto_increment,
startingTime timestamp null default null,
endingTime timestamp null default null,
newThreads int not null,
ignoredThreads int not null,
newComments int not null,
ignoredComments int not null
) engine=innodb;
